import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStrategies, createStrategy, deleteStrategy, getStrategyTypes } from '../api';
import { TrendingUp, Plus, Trash2, Settings, Loader2 } from 'lucide-react';

export default function Strategies() {
  const [strategies, setStrategies] = useState([]);
  const [types, setTypes] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: '', type: 'MA_CROSSOVER', description: '', parameters: {},
  });

  useEffect(() => {
    Promise.all([getStrategies(), getStrategyTypes()])
      .then(([sRes, tRes]) => {
        setStrategies(sRes.data);
        setTypes(tRes.data);
        setForm(prev => ({ ...prev, parameters: tRes.data['MA_CROSSOVER'] || {} }));
      })
      .finally(() => setLoading(false));
  }, []);

  const handleTypeChange = (type) => {
    setForm({ ...form, type, parameters: types[type] || {} });
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      const { data } = await createStrategy(form);
      setStrategies([data, ...strategies]);
      setShowCreate(false);
      setForm({ name: '', type: 'MA_CROSSOVER', description: '', parameters: types['MA_CROSSOVER'] || {} });
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create strategy');
    } finally { setCreating(false); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this strategy?')) return;
    await deleteStrategy(id);
    setStrategies(strategies.filter(s => s.id !== id));
  };

  const TYPE_COLORS = {
    MA_CROSSOVER: 'var(--accent-primary)',
    RSI: 'var(--purple)',
    BOLLINGER: 'var(--cyan)',
    ML_SIGNAL: 'var(--green)',
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Strategies</h2>
          <p>Define and manage your trading strategies</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={16} /> New Strategy
        </button>
      </div>

      {/* Create Strategy Form */}
      {showCreate && (
        <div className="glass-panel animate-fade-in" style={{ marginBottom: 24, padding: '24px' }}>
          <h3 className="card-title" style={{ marginBottom: 20 }}>Create Strategy</h3>
          <form onSubmit={handleCreate}>
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Strategy Name</label>
                <input className="form-input" required placeholder="e.g. Golden Cross AAPL"
                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={form.type}
                  onChange={e => handleTypeChange(e.target.value)}>
                  {Object.keys(types).map(t => (
                    <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Description</label>
              <input className="form-input" placeholder="Optional description"
                value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
            </div>

            {/* Dynamic parameter fields */}
            <div className="form-group">
              <label className="form-label">Parameters</label>
              <div className="grid-2">
                {Object.entries(form.parameters).map(([key, val]) => (
                  <div key={key} className="form-group" style={{ marginBottom: 8 }}>
                    <label className="form-label" style={{ fontSize: 11 }}>{key.replace(/_/g, ' ')}</label>
                    <input className="form-input" type="number" step="any"
                      value={val}
                      onChange={e => setForm({
                        ...form,
                        parameters: { ...form.parameters, [key]: parseFloat(e.target.value) || 0 }
                      })} />
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <button className="btn btn-primary" type="submit" disabled={creating}>
                {creating ? <Loader2 size={16} style={{ animation: 'spin 0.8s linear infinite' }} /> : 'Create'}
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Strategy List */}
      {loading ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
          <Loader2 size={24} style={{ animation: 'spin 0.8s linear infinite' }} />
        </div>
      ) : strategies.length === 0 ? (
        <div className="glass-panel" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div className="empty-state">
            <TrendingUp size={48} />
            <h3>No strategies yet</h3>
            <p>Create your first trading strategy to get started.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
          {strategies.map((s) => (
            <div key={s.id} className="glass-panel" style={{ cursor: 'pointer', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span style={{
                    fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.8,
                    color: TYPE_COLORS[s.type] || 'var(--text-muted)',
                  }}>
                    {s.type.replace(/_/g, ' ')}
                  </span>
                  <h3 style={{ fontSize: 17, fontWeight: 700, marginTop: 4 }}>{s.name}</h3>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}
                  style={{ padding: '6px 8px', color: 'var(--red)' }}>
                  <Trash2 size={14} />
                </button>
              </div>

              {s.description && (
                <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 8 }}>{s.description}</p>
              )}

              <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {Object.entries(s.parameters).map(([k, v]) => (
                  <span key={k} style={{
                    padding: '3px 8px', borderRadius: 6, fontSize: 11, fontFamily: 'var(--font-mono)',
                    background: 'var(--bg-elevated)', color: 'var(--text-secondary)',
                    border: '1px solid var(--border-subtle)',
                  }}>
                    {k}: {v}
                  </span>
                ))}
              </div>

              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                <button className="btn btn-primary btn-sm"
                  onClick={() => navigate('/backtest/new', { state: { strategyId: s.id } })}>
                  Run Backtest
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
