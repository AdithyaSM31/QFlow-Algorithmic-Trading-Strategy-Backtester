import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getStrategies, getSymbols, submitBacktest } from '../api';
import { Rocket, Loader2, AlertCircle } from 'lucide-react';

export default function NewBacktest() {
  const navigate = useNavigate();
  const location = useLocation();
  const [strategies, setStrategies] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    strategy_id: location.state?.strategyId || '',
    symbols: ['AAPL'],
    start_date: '2020-01-01',
    end_date: '2024-12-31',
    initial_capital: 100000,
    slippage_bps: 5,
    commission_pct: 0.1,
  });

  const [symbolInput, setSymbolInput] = useState('');

  useEffect(() => {
    Promise.all([getStrategies(), getSymbols().catch(() => ({ data: [] }))])
      .then(([sRes, symRes]) => {
        setStrategies(sRes.data);
        setSymbols(symRes.data);
        if (!form.strategy_id && sRes.data.length > 0) {
          setForm(prev => ({ ...prev, strategy_id: sRes.data[0].id }));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const addSymbol = () => {
    const sym = symbolInput.trim().toUpperCase();
    if (sym && !form.symbols.includes(sym) && form.symbols.length < 10) {
      setForm({ ...form, symbols: [...form.symbols, sym] });
      setSymbolInput('');
    }
  };

  const removeSymbol = (sym) => {
    setForm({ ...form, symbols: form.symbols.filter(s => s !== sym) });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!form.strategy_id) { setError('Select a strategy'); return; }
    if (form.symbols.length === 0) { setError('Add at least one symbol'); return; }

    setSubmitting(true);
    try {
      const { data } = await submitBacktest(form);
      navigate(`/backtest/${data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit backtest');
    } finally { setSubmitting(false); }
  };

  if (loading) return <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
    <Loader2 size={24} style={{ animation: 'spin 0.8s linear infinite' }} />
  </div>;

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h2>New Backtest</h2>
        <p>Configure and submit a backtest job to the processing queue</p>
      </div>

      <div className="glass-panel" style={{ maxWidth: 720, padding: '24px' }}>
        <form onSubmit={handleSubmit}>
          {/* Strategy Selection */}
          <div className="form-group">
            <label className="form-label">Strategy</label>
            <select className="form-select" value={form.strategy_id} required
              onChange={e => setForm({ ...form, strategy_id: e.target.value })}>
              <option value="">Select a strategy...</option>
              {strategies.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.type.replace(/_/g, ' ')})
                </option>
              ))}
            </select>
            {strategies.length === 0 && (
              <p style={{ color: 'var(--amber)', fontSize: 12, marginTop: 4 }}>
                No strategies found. <a href="/strategies">Create one first</a>.
              </p>
            )}
          </div>

          {/* Symbols */}
          <div className="form-group">
            <label className="form-label">Symbols (max 10)</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="form-input" placeholder="e.g. AAPL"
                value={symbolInput} onChange={e => setSymbolInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addSymbol())} />
              <button className="btn btn-secondary" type="button" onClick={addSymbol}>Add</button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
              {form.symbols.map(sym => (
                <span key={sym} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6, fontSize: 13, fontWeight: 600,
                  fontFamily: 'var(--font-mono)', background: 'var(--accent-glow)',
                  color: 'var(--accent-primary)', border: '1px solid rgba(59,130,246,0.2)',
                }}>
                  {sym}
                  <span onClick={() => removeSymbol(sym)} style={{ cursor: 'pointer', opacity: 0.7 }}>×</span>
                </span>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input className="form-input" type="date" required
                value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">End Date</label>
              <input className="form-input" type="date" required
                value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} />
            </div>
          </div>

          {/* Capital & Costs */}
          <div className="grid-3">
            <div className="form-group">
              <label className="form-label">Initial Capital ($)</label>
              <input className="form-input" type="number" min={1000} step={1000} required
                value={form.initial_capital}
                onChange={e => setForm({ ...form, initial_capital: parseFloat(e.target.value) })} />
            </div>
            <div className="form-group">
              <label className="form-label">Slippage (bps)</label>
              <input className="form-input" type="number" min={0} max={100} step={0.5}
                value={form.slippage_bps}
                onChange={e => setForm({ ...form, slippage_bps: parseFloat(e.target.value) })} />
            </div>
            <div className="form-group">
              <label className="form-label">Commission (%)</label>
              <input className="form-input" type="number" min={0} max={5} step={0.01}
                value={form.commission_pct}
                onChange={e => setForm({ ...form, commission_pct: parseFloat(e.target.value) })} />
            </div>
          </div>

          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
              borderRadius: 8, marginBottom: 16, background: 'var(--red-glow)',
              color: 'var(--red)', fontSize: 13, border: '1px solid rgba(239,68,68,0.2)',
            }}>
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <button className="btn btn-primary btn-lg" type="submit" disabled={submitting}
            style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}>
            {submitting ? (
              <><Loader2 size={18} style={{ animation: 'spin 0.8s linear infinite' }} /> Submitting...</>
            ) : (
              <><Rocket size={18} /> Submit Backtest</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
