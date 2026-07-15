import { useState } from 'react';
import { login, register, getMe } from '../api';
import { Activity, ArrowRight, Loader2 } from 'lucide-react';

export default function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({ email: '', username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(form);
      }
      const { data } = await login({ username: form.username, password: form.password });
      localStorage.setItem('qflow_token', data.access_token);
      const me = await getMe();
      onLogin(me.data, data.access_token);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px', position: 'relative', zIndex: 1
    }}>
      <div className="auth-container animate-fade-in">
        
        {/* Left Side: Hero Typgraphy */}
        <div className="auth-hero animate-slide-in">
          <h1 className="heading-hero text-glow" style={{ marginBottom: '16px' }}>
            THE MOST<br/>
            INTELLIGENT WAY TO<br/>
            <span className="text-glow-accent" style={{ color: 'var(--neon-orange)' }}>
              BACKTEST STRATEGIES
            </span>
          </h1>
          <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '400px' }}>
            The proven QFlow Engine, amplified with high-performance time-series analytics and zero look-ahead bias.
          </p>
        </div>

        {/* Right Side: Form Card */}
        <div className="auth-card animate-fade-in">
          <div className="glass-panel" style={{ padding: '40px' }}>
            
            {/* Logo */}
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <img src="/logo.png" alt="QFlow Logo" style={{
                width: '160px', height: 'auto', objectFit: 'contain', marginBottom: '16px'
              }} />
              <h2 style={{ fontSize: '24px', fontWeight: '800' }}>
                {isRegister ? 'Create Account' : 'Welcome Back'}
              </h2>
            </div>

            <form onSubmit={handleSubmit}>
              {isRegister && (
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <input
                    className="form-input" type="email" required
                    placeholder="you@example.com"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Username</label>
                <input
                  className="form-input" type="text" required
                  placeholder="Enter username"
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  className="form-input" type="password" required
                  placeholder="••••••••" minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </div>

              {error && (
                <div style={{
                  padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: '20px',
                  background: 'rgba(239,68,68,0.1)', color: 'var(--neon-red)',
                  fontSize: '14px', border: '1px solid rgba(239,68,68,0.3)',
                  boxShadow: '0 0 10px rgba(239,68,68,0.2)'
                }}>
                  {error}
                </div>
              )}

              <button className="btn btn-primary btn-lg" type="submit" disabled={loading}
                style={{ width: '100%', justifyContent: 'center' }}>
                {loading ? <Loader2 size={18} className="animate-spin" /> : (
                  <>{isRegister ? 'Create Account' : 'Sign In'} <ArrowRight size={18} /></>
                )}
              </button>
            </form>

            <p style={{
              textAlign: 'center', marginTop: '24px', fontSize: '14px', color: 'var(--text-muted)'
            }}>
              {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
              <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(!isRegister); setError(''); }}
                style={{ color: 'var(--neon-orange)', fontWeight: '600' }}>
                {isRegister ? 'Sign In' : 'Register'}
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
