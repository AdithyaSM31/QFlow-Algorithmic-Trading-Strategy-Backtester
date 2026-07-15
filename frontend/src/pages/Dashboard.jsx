import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getBacktests, getStrategies, getWsUrl } from '../api';
import { Activity, TrendingUp, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

const STATUS_BADGE = {
  PENDING: 'badge-pending',
  RUNNING: 'badge-running',
  COMPLETED: 'badge-completed',
  FAILED: 'badge-failed',
};

export default function Dashboard() {
  const [backtests, setBacktests] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = () => {
      Promise.all([
        getBacktests({ limit: 20 }),
        getStrategies(),
      ]).then(([btRes, stRes]) => {
        setBacktests(btRes.data);
        setStrategies(stRes.data);
      }).catch(() => {})
        .finally(() => setLoading(false));
    };

    fetchData();

    const ws = new WebSocket(getWsUrl());
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        setBacktests(prev => prev.map(bt => 
          bt.id === msg.backtest_id 
            ? { ...bt, progress: msg.progress, status: msg.status } 
            : bt
        ));
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };

    return () => ws.close();
  }, []);

  const completed = backtests.filter(b => b.status === 'COMPLETED');
  const running = backtests.filter(b => b.status === 'RUNNING');
  const failed = backtests.filter(b => b.status === 'FAILED');

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of your trading strategies and backtest performance</p>
      </div>

      {/* Metrics */}
      <div className="metrics-grid">
        <div className="metric-card glass-panel">
          <div className="metric-label">Total Strategies</div>
          <div className="metric-value" style={{ color: 'var(--accent-primary)' }}>
            {loading ? '—' : strategies.length}
          </div>
          <div className="metric-subtitle">Active configurations</div>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-label">Backtests Run</div>
          <div className="metric-value" style={{ color: 'var(--purple)' }}>
            {loading ? '—' : backtests.length}
          </div>
          <div className="metric-subtitle">All time</div>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-label">Completed</div>
          <div className="metric-value positive">
            {loading ? '—' : completed.length}
          </div>
          <div className="metric-subtitle">Successful runs</div>
        </div>

        <div className="metric-card glass-panel">
          <div className="metric-label">Running</div>
          <div className="metric-value" style={{ color: 'var(--cyan)' }}>
            {loading ? '—' : running.length}
          </div>
          <div className="metric-subtitle">In progress</div>
        </div>
      </div>

      {/* Recent Backtests Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div className="card-header">
          <h3 className="card-title">Recent Backtests</h3>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/backtest/new')}>
            + New Backtest
          </button>
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={24} style={{ animation: 'spin 0.8s linear infinite' }} />
          </div>
        ) : backtests.length === 0 ? (
          <div className="empty-state">
            <Activity size={48} />
            <h3>No backtests yet</h3>
            <p>Create a strategy and run your first backtest to see results here.</p>
            <button className="btn btn-primary mt-4" onClick={() => navigate('/strategies')}>
              Create Strategy
            </button>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Symbols</th>
                  <th>Date Range</th>
                  <th>Capital</th>
                  <th>Progress</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {backtests.map((bt) => (
                  <tr key={bt.id} onClick={() => navigate(`/backtest/${bt.id}`)}
                    style={{ cursor: 'pointer' }}>
                    <td>
                      <span className={`badge ${STATUS_BADGE[bt.status] || ''}`}>
                        {bt.status === 'RUNNING' && <Loader2 size={12} style={{ animation: 'spin 0.8s linear infinite' }} />}
                        {bt.status === 'COMPLETED' && <CheckCircle2 size={12} />}
                        {bt.status === 'FAILED' && <XCircle size={12} />}
                        {bt.status === 'PENDING' && <Clock size={12} />}
                        {bt.status}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {bt.symbols.join(', ')}
                    </td>
                    <td>{bt.start_date} → {bt.end_date}</td>
                    <td>${bt.initial_capital?.toLocaleString()}</td>
                    <td>
                      <div className="progress-bar" style={{ width: 80 }}>
                        <div className="progress-bar-fill" style={{ width: `${bt.progress * 100}%` }} />
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(bt.submitted_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
