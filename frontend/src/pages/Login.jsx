import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../toast.jsx';
import { ErrorMessage } from '../components.jsx';
import AuthLayout, { PasswordInput } from './AuthLayout.jsx';

export default function Login() {
  const { setUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [needCode, setNeedCode] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  function done(user) {
    setUser(user);
    toast(`Welcome back, @${user.username}!`);
    navigate(user.role === 'organizer' ? (user.totp_enabled ? '/organizer' : '/2fa/setup') : '/');
  }

  async function submitPassword(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post('/auth/login', { username: username.trim(), password });
      setPassword('');
      if (res.mfa_required) setNeedCode(true);
      else done(res.user);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      done((await api.post('/auth/login/2fa', { code })).user);
    } catch (err) {
      setCode('');
      setError(err);
      if (err.message.includes('log in again')) setNeedCode(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title={needCode ? 'One more step' : 'The show goes on'} tagline="Log in to see your tickets, or to run your events.">
      {!needCode ? (
        <>
          <h1>Log in</h1>
          <ErrorMessage error={error} />
          <form onSubmit={submitPassword}>
            <label>Username
              <input required autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={30}
                value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. jean.paul" autoFocus />
            </label>
            <PasswordInput label="Password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            <button type="submit" className="big" style={{ width: '100%' }} disabled={busy}>{busy ? 'Checking…' : 'Log in'}</button>
          </form>
          <p className="hint">New here? <Link to="/register">Create an account</Link></p>
        </>
      ) : (
        <>
          <h1>Enter your code</h1>
          <p className="hint">Open your authenticator app and type the 6-digit code for SecureSeat.</p>
          <ErrorMessage error={error} />
          <form onSubmit={submitCode}>
            <input className="code-input" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" required autoFocus
              aria-label="6-digit code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} placeholder="••••••" />
            <button type="submit" className="big" style={{ width: '100%', marginTop: 14 }} disabled={busy || code.length !== 6}>Verify</button>
          </form>
        </>
      )}
    </AuthLayout>
  );
}
