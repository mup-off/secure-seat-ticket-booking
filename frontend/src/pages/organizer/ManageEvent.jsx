// Overview of a published (or paused, ended, cancelled) event, with its status actions.
import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { api } from '../../api.js';
import { useApi } from '../../useApi.js';
import { useToast } from '../../toast.jsx';
import { ErrorMessage, Status } from '../../components.jsx';
import { rwf, when } from '../../format.js';
import { Bar, CountUp, Skeleton } from '../../ui.jsx';

export default function ManageEvent() {
  const { id } = useParams();
  const toast = useToast();
  const { data: event, error: loadError, reload } = useApi(`/organizer/events/${id}`);
  const [error, setError] = useState(null);
  const [confirming, setConfirming] = useState(false);

  async function act(action) {
    setError(null);
    try {
      const res = await api.post(`/organizer/events/${id}/${action}`);
      if (res.refunds) {
        const r = res.refunds;
        toast(`Event cancelled. ${r.refunded} of ${r.refunds_started} paid order(s) refunded; ${r.holds_released} reservation(s) released.`, 'info');
      } else {
        toast(action === 'pause' ? 'Sales paused.' : 'Sales are back on!');
      }
      setConfirming(false);
      await reload();
    } catch (err) {
      setError(err);
    }
  }

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!event) return <Skeleton height={200} count={2} />;
  if (event.status === 'draft') return <Navigate to={`/organizer/events/${id}/edit`} replace />;
  const live = ['published', 'paused'].includes(event.status);
  const sold = event.ticket_types.reduce((n, t) => n + t.sold, 0);
  const capacity = event.ticket_types.reduce((n, t) => n + t.capacity, 0);

  return (
    <>
      <p><Link to="/organizer">← My events</Link></p>
      <section className="card">
        <div className="row">
          <div>
            <span className="eyebrow">{when(event.starts_at)}</span>
            <h1>{event.title}</h1>
          </div>
          <Status value={event.status} />
        </div>
        <p className="hint">{event.online_url ? 'Online event' : `${event.venue}, ${event.venue_address}`}</p>
        <div className="row-left">
          <Link className="button secondary" to={`/events/${event.id}`}>View public page</Link>
          <Link className="button secondary" to={`/organizer/events/${event.id}/attendees`}>Attendees</Link>
          {live && <Link className="button secondary" to={`/organizer/events/${event.id}/edit?step=1`}>Edit details</Link>}
          {live && <Link className="button secondary" to={`/organizer/events/${event.id}/edit?step=2`}>Edit ticket types</Link>}
          {event.status === 'published' && <button type="button" className="secondary" onClick={() => act('pause')}>Pause sales</button>}
          {event.status === 'paused' && <button type="button" onClick={() => act('resume')}>Resume sales</button>}
        </div>
        <ErrorMessage error={error} />
      </section>

      <div className="stats">
        <div className="stat" style={{ '--i': 0 }}><b><CountUp value={sold} /></b><small>Sold or held</small></div>
        <div className="stat" style={{ '--i': 1 }}><b><CountUp value={Math.max(capacity - sold, 0)} /></b><small>Still available</small></div>
        <div className="stat" style={{ '--i': 2 }}><b>{capacity ? Math.round((sold / capacity) * 100) : 0}%</b><small>Of capacity</small></div>
      </div>

      <section className="card">
        <h2>Ticket types</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Price</th><th>Sales</th><th>Status</th></tr></thead>
            <tbody>
              {event.ticket_types.map((t) => (
                <tr key={t.id}>
                  <td><strong>{t.name}</strong> {t.visibility === 'hidden' && <span className="badge">Hidden</span>}</td>
                  <td>{rwf(t.price)}</td>
                  <td style={{ minWidth: 160 }}><span className="hint">{t.sold} / {t.capacity}</span><Bar value={t.sold} max={t.capacity} low={-1} /></td>
                  <td>{t.on_sale ? <span className="status published">On sale</span> : <span className="status paused">Stopped</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {live && (
        <section className="card danger">
          <h2>Cancel event</h2>
          <p>Stops all sales, releases unpaid reservations and refunds everyone who paid. This can't be undone and is recorded in the audit log.</p>
          {!confirming ? (
            <button type="button" className="danger" onClick={() => setConfirming(true)}>Cancel event…</button>
          ) : (
            <div className="row-left">
              <strong>Refund all {sold} ticket(s) and cancel?</strong>
              <button type="button" className="danger" onClick={() => act('cancel')}>Yes, cancel and refund</button>
              <button type="button" className="secondary" onClick={() => setConfirming(false)}>Keep the event</button>
            </div>
          )}
        </section>
      )}
    </>
  );
}
