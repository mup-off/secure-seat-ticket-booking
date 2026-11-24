import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { ErrorMessage } from '../components.jsx';

export default function Register() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', confirm: '', role: 'buyer' });
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (form.password !== form.confirm) return setError(new Error('Passwords do not match.'));
    try {
      const res = await api.post('/auth/register', { email: form.email, password: form.password, role: form.role });
      setUser(res.user);
      navigate(res.user.role === 'organizer' ? '/2fa/setup' : '/');
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section className="card narrow">
      <h1>Create an account</h1>
      <ErrorMessage error={error} />
      <form onSubmit={submit}>
        <label>Email <input type="email" required maxLength={254} autoComplete="email" value={form.email} onChange={set('email')} /></label>
        <label>Password <input type="password" required minLength={10} maxLength={128} autoComplete="new-password" value={form.password} onChange={set('password')} /></label>
        <label>Confirm password <input type="password" required minLength={10} maxLength={128} autoComplete="new-password" value={form.confirm} onChange={set('confirm')} /></label>
        <fieldset>
          <legend>I want to</legend>
          <label className="radio"><input type="radio" name="role" value="buyer" checked={form.role === 'buyer'} onChange={set('role')} /> Buy tickets</label>
          <label className="radio"><input type="radio" name="role" value="organizer" checked={form.role === 'organizer'} onChange={set('role')} /> Sell tickets for my events (needs an authenticator app)</label>
        </fieldset>
        <p className="hint">At least 10 characters. A short sentence is easy to remember and hard to guess.</p>
        <button type="submit">Sign up</button>
      </form>
    </section>
  );
}
