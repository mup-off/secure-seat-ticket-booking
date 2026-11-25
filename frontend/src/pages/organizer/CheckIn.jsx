// Gate check-in: built for speed. The box stays focused after every scan (a USB or
// phone barcode scanner types the code and presses Enter), and the result flashes
// green or red so staff can see it at a glance.
import { useRef, useState } from 'react';
import { api, ApiError } from '../../api.js';
import { when } from '../../format.js';

export default function CheckIn() {
  const [token, setToken] = useState('');
  const [outcome, setOutcome] = useState(null);
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const seq = useRef(0);

  async function submit(e) {
    e.preventDefault();
    if (!token.trim()) return;
    setBusy(true);
    let result;
    try {
      result = await api.post('/organizer/checkin', { token: token.trim() });
    } catch (err) {
      result = err instanceof ApiError && err.body?.result ? err.body : { result: 'error', message: err.message };
    }
    seq.current += 1;
    setOutcome({ ...result, key: seq.current });
    setLog((l) => [{ key: seq.current, at: new Date(), result: result.result, label: result.ticket_type ? `${result.ticket_type} · ${result.event}` : 'Unknown code' }, ...l].slice(0, 8));
    setToken('');
    setBusy(false);
    input.current?.focus();
  }

  const good = outcome?.result === 'ok';
  const counts = log.reduce((c, x) => ({ ...c, [x.result === 'ok' ? 'ok' : 'bad']: (c[x.result === 'ok' ? 'ok' : 'bad'] || 0) + 1 }), {});

  return (
    <div className="event-layout">
      <div>
        <span className="eyebrow">Gate</span>
        <h1>Check-in</h1>
        {outcome && (
          <div key={outcome.key} className={`scan-result ${good ? 'ok' : 'bad'}`} role="alert">
            <b>{good ? 'Let them in' : outcome.result === 'already_used' ? 'Already used' : 'Not valid'}</b>
            {good && <p>{outcome.ticket_type} · {outcome.event}</p>}
            {outcome.result === 'already_used' && <p>This ticket was checked in at {when(outcome.checked_in_at)}. Do not let them in.</p>}
            {outcome.result === 'invalid' && <p>This code isn't a paid ticket for one of your events.</p>}
            {outcome.result === 'error' && <p>{outcome.message}</p>}
          </div>
        )}
        <form onSubmit={submit} className="card">
          <label>Ticket code (type, paste or scan)
            <input ref={input} className="code-input" style={{ fontSize: '1rem', letterSpacing: '0.05em' }} required maxLength={60}
              autoComplete="off" autoFocus value={token} onChange={(e) => setToken(e.target.value)} />
          </label>
          <button type="submit" className="big" style={{ width: '100%' }} disabled={busy}>Check in</button>
        </form>
      </div>
      <aside>
        <section className="card">
          <h2>This session</h2>
          <p className="hint">{counts.ok || 0} admitted · {counts.bad || 0} refused</p>
          {!log.length && <p className="empty">Scans appear here.</p>}
          <ul className="scan-log">
            {log.map((x) => (
              <li key={x.key}>
                <span>{x.result === 'ok' ? '✓' : '✗'} {x.label}</span>
                <span>{x.at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              </li>
            ))}
          </ul>
        </section>
      </aside>
    </div>
  );
}
