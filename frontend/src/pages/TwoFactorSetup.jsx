import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { ErrorMessage } from '../components.jsx';

export default function TwoFactorSetup() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);

  const needsSetup = user && user.role === 'organizer' && !user.totp_enabled;
  useEffect(() => {
    if (needsSetup) api.get('/auth/2fa/setup').then(setSetup, setError);
  }, [needsSetup]);

  if (user === undefined) return <p className="empty">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!needsSetup) return <Navigate to="/" replace />;

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post('/auth/2fa/setup', { code });
      setUser(res.user);
      navigate('/organizer');
    } catch (err) {
      setCode('');
      setError(err);
    }
  }

  return (
    <section className="card narrow">
      <h1>Set up two-step verification</h1>
      <p>Organizers must use an authenticator app (Google Authenticator, Microsoft Authenticator, Authy…), because your account can see attendee details.</p>
      {setup && (
        <ol>
          <li>In the app, choose <strong>Add account</strong>, then <strong>Enter a setup key</strong>.</li>
          <li>Enter this key, as a time-based key:
            <p className="secret"><code>{setup.secret.match(/.{1,4}/g).join(' ')}</code></p>
          </li>
          <li>Type the 6-digit code the app shows.</li>
        </ol>
      )}
      <ErrorMessage error={error} />
      <form onSubmit={submit}>
        <label>Code <input inputMode="numeric" pattern="[0-9 ]{6,7}" maxLength={7} autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)} /></label>
        <button type="submit">Turn on</button>
      </form>
    </section>
  );
}
