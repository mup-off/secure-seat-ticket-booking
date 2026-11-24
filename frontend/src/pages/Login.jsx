import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { ErrorMessage } from '../components.jsx';

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [needCode, setNeedCode] = useState(false);
  const [error, setError] = useState(null);

  function done(user) {
    setUser(user);
    navigate(user.role === 'organizer' ? (user.totp_enabled ? '/organizer' : '/2fa/setup') : '/');
  }

  async function submitPassword(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post('/auth/login', { email, password });
      setPassword('');
      if (res.mfa_required) setNeedCode(true);
      else done(res.user);
    } catch (err) {
      setError(err);
    }
  }

  async function submitCode(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post('/auth/login/2fa', { code });
      done(res.user);
    } catch (err) {
      setCode('');
      setError(err);
      if (err.message.includes('log in again')) setNeedCode(false);
    }
  }

  return (
    <section className="card narrow">
      {!needCode ? (
        <>
          <h1>Log in</h1>
          <ErrorMessage error={error} />
          <form onSubmit={submitPassword}>
            <label>Email <input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label>Password <input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
            <button type="submit">Log in</button>
          </form>
          <p>No account? <Link to="/register">Sign up</Link></p>
        </>
      ) : (
        <>
          <h1>Enter your code</h1>
          <p>Open your authenticator app and enter the 6-digit code for SecureSeat.</p>
          <ErrorMessage error={error} />
          <form onSubmit={submitCode}>
            <label>Code <input inputMode="numeric" pattern="[0-9 ]{6,7}" maxLength={7} autoComplete="one-time-code" required autoFocus value={code} onChange={(e) => setCode(e.target.value)} /></label>
            <button type="submit">Verify</button>
          </form>
        </>
      )}
    </section>
  );
}
