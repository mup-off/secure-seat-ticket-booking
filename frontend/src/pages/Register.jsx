import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useToast } from '../toast.jsx';
import { ErrorMessage } from '../components.jsx';
import { SCORE_LABELS, passwordScore } from '../ui.jsx';
import AuthLayout, { PasswordInput } from './AuthLayout.jsx';

const USERNAME_RE = /^[a-z0-9][a-z0-9._-]{2,29}$/;

// Asks the server whether a username is free, a moment after the person stops typing.
function useUsernameCheck(raw) {
  const [state, setState] = useState(null);
  useEffect(() => {
    const name = raw.trim().toLowerCase();
    if (!name) { setState(null); return undefined; }
    if (!USERNAME_RE.test(name)) {
      setState({ available: false, reason: 'Use 3–30 letters, numbers, dots, dashes or underscores.' });
      return undefined;
    }
    setState({ checking: true });
    const t = setTimeout(async () => {
      try {
        setState(await api.get(`/auth/username-available?username=${encodeURIComponent(name)}`));
      } catch {
        setState(null); // e.g. rate-limited: the server still checks on sign-up
      }
    }, 450);
    return () => clearTimeout(t);
  }, [raw]);
  return state;
}

export default function Register() {
  const { setUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '', role: 'buyer' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const check = useUsernameCheck(form.username);
  const score = passwordScore(form.password, form.username);
  const mismatch = form.confirm && form.confirm !== form.password;

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (form.password !== form.confirm) return setError(new Error('Passwords do not match.'));
    setBusy(true);
    try {
      const res = await api.post('/auth/register', {
        username: form.username.trim().toLowerCase(), email: form.email, password: form.password, role: form.role,
      });
      setUser(res.user);
      toast(`Welcome to SecureSeat, @${res.user.username}!`);
      navigate(res.user.role === 'organizer' ? '/2fa/setup' : '/');
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Grab a seat" tagline="One account for every concert, conference, match and service in Kigali.">
      <h1>Create an account</h1>
      <ErrorMessage error={error} />
      <form onSubmit={submit}>
        <div className="role-cards" role="radiogroup" aria-label="Account type">
          <button type="button" role="radio" aria-checked={form.role === 'buyer'} className={`role-card ${form.role === 'buyer' ? 'on' : ''}`} onClick={() => setForm({ ...form, role: 'buyer' })}>
            <b>I'm going</b><span>Buy tickets to events</span>
          </button>
          <button type="button" role="radio" aria-checked={form.role === 'organizer'} className={`role-card ${form.role === 'organizer' ? 'on' : ''}`} onClick={() => setForm({ ...form, role: 'organizer' })}>
            <b>I'm hosting</b><span>Sell tickets (needs an authenticator app)</span>
          </button>
        </div>

        <label>Username
          {check?.checking && <span className="hint"> checking…</span>}
          {check?.available === true && <span className="field-ok">✓ available</span>}
          {check?.available === false && <span className="field-error">{check.reason}</span>}
          <input required maxLength={30} autoComplete="username" autoCapitalize="none" spellCheck={false}
            value={form.username} onChange={set('username')} placeholder="e.g. jean.paul" />
        </label>
        <label>Email <span className="hint">(for your tickets; not used to log in)</span>
          <input type="email" required maxLength={254} autoComplete="email" value={form.email} onChange={set('email')} />
        </label>
        <PasswordInput label="Password" value={form.password} onChange={set('password')} autoComplete="new-password" minLength={10}>
          <div className="meter" data-score={form.password ? score : 0} aria-hidden="true"><span /><span /><span /><span /></div>
          <div className="meter-label">{form.password ? SCORE_LABELS[score] : 'At least 10 characters. A short sentence works well.'}</div>
        </PasswordInput>
        <PasswordInput label="Confirm password" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" minLength={10}>
          {mismatch && <span className="field-error">Passwords don't match yet</span>}
          {form.confirm && !mismatch && <span className="field-ok">✓ matches</span>}
        </PasswordInput>
        <button type="submit" className="big" style={{ width: '100%' }} disabled={busy || check?.available === false || mismatch}>
          {busy ? 'Creating your account…' : 'Create account'}
        </button>
      </form>
      <p className="hint">Already have an account? <Link to="/login">Log in</Link></p>
    </AuthLayout>
  );
}
