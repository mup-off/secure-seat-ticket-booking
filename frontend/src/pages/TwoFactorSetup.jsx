import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../toast.jsx';
import { ErrorMessage } from '../components.jsx';
import { QrImage, Skeleton } from '../ui.jsx';

export default function TwoFactorSetup() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [showKey, setShowKey] = useState(false);

  const needsSetup = user && user.role === 'organizer' && !user.totp_enabled;
  useEffect(() => {
    if (needsSetup) api.get('/auth/2fa/setup').then(setSetup, setError);
  }, [needsSetup]);

  if (user === undefined) return <Skeleton height={300} />;
  if (!user) return <Navigate to="/login" replace />;
  if (!needsSetup) return <Navigate to="/" replace />;

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.post('/auth/2fa/setup', { code });
      setUser(res.user);
      toast('Two-step verification is on. Your account is protected.');
      navigate('/organizer');
    } catch (err) {
      setCode('');
      setError(err);
    }
  }

  return (
    <section className="card narrow">
      <span className="eyebrow">Step 2 of sign-up</span>
      <h1>Protect your account</h1>
      <p className="hint">Organizers can see attendee details, so we ask for a code from an authenticator app (Google Authenticator, Microsoft Authenticator, Authy…) at every login.</p>
      {setup ? (
        <>
          <p><strong>1.</strong> In the app, tap <strong>Add account</strong> and scan this code:</p>
          <div className="qr-box"><QrImage value={setup.uri} alt="Setup QR code for your authenticator app" /></div>
          <p className="hint">
            Can't scan? <button type="button" className="link" onClick={() => setShowKey(!showKey)}>{showKey ? 'Hide' : 'Show'} the setup key</button>
          </p>
          {showKey && <p className="secret"><code>{setup.secret.match(/.{1,4}/g).join(' ')}</code></p>}
        </>
      ) : (
        <Skeleton height={200} />
      )}
      <p><strong>2.</strong> Type the 6-digit code the app shows:</p>
      <ErrorMessage error={error} />
      <form onSubmit={submit}>
        <input className="code-input" inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" required
          aria-label="6-digit code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} placeholder="••••••" />
        <button type="submit" className="big" style={{ width: '100%', marginTop: 14 }} disabled={code.length !== 6}>Turn on</button>
      </form>
    </section>
  );
}
