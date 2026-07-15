import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBacktest, getEquityCurve, getTrades } from '../api';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  ArrowLeft, Loader2, TrendingUp, TrendingDown,
  DollarSign, BarChart3, Target, Activity, Percent,
} from 'lucide-react';

const STATUS_BADGE = {
  PENDING: 'badge-pending', RUNNING: 'badge-running',
  COMPLETED: 'badge-completed', FAILED: 'badge-failed',
};

export default function BacktestResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [equity, setEquity] = useState([]);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('equity');

  useEffect(() => {
    loadData();
    
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/progress');
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.backtest_id === id) {
          setData(prev => {
            if (!prev) return prev;
            return {
              ...prev,
              backtest: {
                ...prev.backtest,
                progress: msg.progress,
                status: msg.status,
                error_message: msg.error || prev.backtest.error_message
              }
            };
          });
          if (msg.status === 'COMPLETED' || msg.status === 'FAILED') {
            loadData();
          }
        }
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };

    return () => ws.close();
  }, [id]);

  const loadData = async () => {
    try {
      const btRes = await getBacktest(id);
      setData(btRes.data);
      if (btRes.data.backtest.status === 'COMPLETED') {
        const [eqRes, trRes] = await Promise.all([getEquityCurve(id), getTrades(id)]);
        setEquity(eqRes.data.map(p => ({
          ...p,
          date: new Date(p.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }),
          drawdown: Math.min(0, p.cumulative_return - Math.max(...eqRes.data.slice(0, eqRes.data.indexOf(p) + 1).map(x => x.cumulative_return))) * 100,
        })));
        setTrades(trRes.data);
      }
    } catch (err) {
      console.error(err);
    } finally { setLoading(false); }
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
      <Loader2 size={32} style={{ animation: 'spin 0.8s linear infinite', color: 'var(--accent-primary)' }} />
    </div>
  );

  if (!data) return <div>Backtest not found</div>;

  const { backtest, analytics } = data;
  const isComplete = backtest.status === 'COMPLETED';

  const fmtPct = (v) => v != null ? `${(v * 100).toFixed(2)}%` : '—';
  const fmtNum = (v, d = 2) => v != null ? v.toFixed(d) : '—';
  const fmtMoney = (v) => v != null ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—';

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/')}>
          <ArrowLeft size={16} />
        </button>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700 }}>
              {data.strategy_name || 'Backtest'} — {backtest.symbols.join(', ')}
            </h2>
            <span className={`badge ${STATUS_BADGE[backtest.status]}`}>{backtest.status}</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {data.strategy_type?.replace(/_/g, ' ')} · {backtest.start_date} → {backtest.end_date} · {fmtMoney(backtest.initial_capital)} capital
          </p>
        </div>
      </div>

      {/* Progress for running */}
      {backtest.status === 'RUNNING' && (
        <div className="glass-panel" style={{ marginBottom: 24, padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <Loader2 size={18} style={{ animation: 'spin 0.8s linear infinite', color: 'var(--accent-primary)' }} />
            <span style={{ fontWeight: 600 }}>Backtest in progress...</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {(backtest.progress * 100).toFixed(0)}%
            </span>
          </div>
          <div className="progress-bar" style={{ height: 8 }}>
            <div className="progress-bar-fill" style={{ width: `${backtest.progress * 100}%` }} />
          </div>
        </div>
      )}

      {/* Error */}
      {backtest.status === 'FAILED' && (
        <div className="glass-panel" style={{ marginBottom: 24, padding: '24px', borderColor: 'rgba(239,68,68,0.3)' }}>
          <p style={{ color: 'var(--red)', fontWeight: 600 }}>Backtest Failed</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            {backtest.error_message || 'Unknown error'}
          </p>
        </div>
      )}

      {/* Analytics Metrics */}
      {isComplete && analytics && (
        <>
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <MetricCard label="Total Return" value={fmtPct(analytics.total_return)}
              positive={analytics.total_return > 0} icon={<TrendingUp size={16} />} />
            <MetricCard label="Sharpe Ratio" value={fmtNum(analytics.sharpe_ratio)}
              positive={analytics.sharpe_ratio > 1} icon={<Target size={16} />} />
            <MetricCard label="Max Drawdown" value={fmtPct(analytics.max_drawdown)}
              positive={false} icon={<TrendingDown size={16} />} />
            <MetricCard label="Win Rate" value={fmtPct(analytics.win_rate)}
              positive={analytics.win_rate > 0.5} icon={<Percent size={16} />} />
            <MetricCard label="Total Trades" value={analytics.total_trades}
              icon={<Activity size={16} />} />
          </div>

          {/* Secondary Metrics */}
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
            <MetricCard label="Annualized" value={fmtPct(analytics.annualized_return)}
              positive={analytics.annualized_return > 0} small />
            <MetricCard label="Sortino" value={fmtNum(analytics.sortino_ratio)} small />
            <MetricCard label="Calmar" value={fmtNum(analytics.calmar_ratio)} small />
            <MetricCard label="Profit Factor" value={fmtNum(analytics.profit_factor)} small />
            <MetricCard label="Volatility" value={fmtPct(analytics.volatility)} small />
          </div>

          {/* Tab Navigation */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
            {['equity', 'drawdown', 'returns', 'trades'].map(tab => (
              <button key={tab} className={`btn btn-sm ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab(tab)}>
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Equity Curve */}
          {activeTab === 'equity' && equity.length > 0 && (
            <div className="chart-container">
              <h3>📈 Equity Curve</h3>
              <ResponsiveContainer width="100%" height={380}>
                <AreaChart data={equity}>
                  <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }}
                    tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{
                    background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, fontSize: 13, color: '#f0f4f8',
                  }} />
                  <Area type="monotone" dataKey="portfolio_value" stroke="#3b82f6"
                    fill="url(#eqGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Drawdown Chart */}
          {activeTab === 'drawdown' && equity.length > 0 && (
            <div className="chart-container">
              <h3>📉 Drawdown</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={equity}>
                  <defs>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `${v.toFixed(0)}%`} />
                  <Tooltip contentStyle={{
                    background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, fontSize: 13,
                  }} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                  <Area type="monotone" dataKey="drawdown" stroke="#ef4444"
                    fill="url(#ddGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Daily Returns */}
          {activeTab === 'returns' && equity.length > 0 && (
            <div className="chart-container">
              <h3>📊 Daily Returns Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={equity.filter((_, i) => i % 5 === 0)}>
                  <CartesianGrid stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickFormatter={v => `${(v * 100).toFixed(1)}%`} />
                  <Tooltip contentStyle={{
                    background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, fontSize: 13,
                  }} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                  <Bar dataKey="daily_return" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trades Table */}
          {activeTab === 'trades' && (
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 className="card-title" style={{ marginBottom: 16 }}>Trade Log ({trades.length} trades)</h3>
              {trades.length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No trades executed.</p>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Date</th><th>Symbol</th><th>Side</th><th>Qty</th>
                        <th>Price</th><th>Fill Price</th><th>Slippage</th>
                        <th>Commission</th><th>P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.map((t) => (
                        <tr key={t.id}>
                          <td>{new Date(t.timestamp).toLocaleDateString()}</td>
                          <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                          <td>
                            <span style={{
                              color: t.side === 'BUY' ? 'var(--green)' : 'var(--red)',
                              fontWeight: 600,
                            }}>{t.side}</span>
                          </td>
                          <td>{t.quantity}</td>
                          <td>${t.price.toFixed(2)}</td>
                          <td>${t.fill_price.toFixed(2)}</td>
                          <td>${t.slippage.toFixed(2)}</td>
                          <td>${t.commission.toFixed(2)}</td>
                          <td style={{
                            color: t.pnl != null ? (t.pnl > 0 ? 'var(--green)' : 'var(--red)') : 'var(--text-muted)',
                            fontWeight: 600,
                          }}>
                            {t.pnl != null ? `$${t.pnl.toFixed(2)}` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value, positive, icon, small }) {
  return (
    <div className="metric-card glass-panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: small ? 4 : 8 }}>
        {icon && <span style={{ color: 'var(--text-muted)' }}>{icon}</span>}
        <span className="metric-label" style={{ marginBottom: 0 }}>{label}</span>
      </div>
      <div className={`metric-value ${positive === true ? 'positive' : positive === false ? 'negative' : ''}`}
        style={{ fontSize: small ? 20 : 28 }}>
        {value}
      </div>
    </div>
  );
}
