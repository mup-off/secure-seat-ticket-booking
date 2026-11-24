import { useState } from 'react';
import { api, ApiError } from '../../api.js';
import { when } from '../../format.js';

export default function CheckIn() {
  const [token, setToken] = useState('');
  const [outcome, setOutcome] = useState(null);

  async function submit(e) {
    e.preventDefault();
    try {
      setOutcome(await api.post('/organizer/checkin', { token: token.trim() }));
    } catch (err) {
      setOutcome(err instanceof ApiError && err.body?.result ? err.body : { result: 'error', message: err.message });
    }
    setToken('');
  }

  return (
    <section className="card narrow">
      <h1>Gate check-in</h1>
      {outcome?.result === 'ok' && <p className="ok" role="status">Valid ticket: {outcome.ticket_type}, {outcome.event}. Let them in.</p>}
      {outcome?.result === 'already_used' && <p className="error" role="alert">Already used at {when(outcome.checked_in_at)}. Do not let them in.</p>}
      {outcome?.result === 'invalid' && <p className="error" role="alert">Not a valid ticket for your events.</p>}
      {outcome?.result === 'error' && <p className="error" role="alert">{outcome.message}</p>}
      <form onSubmit={submit}>
        <label>Ticket code <input required maxLength={60} autoComplete="off" autoFocus value={token} onChange={(e) => setToken(e.target.value)} /></label>
        <button type="submit">Check in</button>
      </form>
    </section>
  );
}
