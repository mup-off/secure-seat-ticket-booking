// Overview of a published (or paused, ended, cancelled) event, with its status actions.
import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { api } from '../../api.js';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { rwf, when } from '../../format.js';

export default function ManageEvent() {
  const { id } = useParams();
  const { data: event, error: loadError, reload } = useApi(`/organizer/events/${id}`);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  async function act(action, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setError(null);
    setMessage(null);
    try {
      const res = await api.post(`/organizer/events/${id}/${action}`);
      if (res.refunds) {
        const r = res.refunds;
        setMessage(`Event cancelled. ${r.refunded} of ${r.refunds_started} paid order(s) refunded; ${r.holds_released} unpaid reservation(s) released.`);
      }
      await reload();
    } catch (err) {
      setError(err);
    }
  }

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!event) return <p className="empty">Loading…</p>;
  if (event.status === 'draft') return <Navigate to={`/organizer/events/${id}/edit`} replace />;
  const live = ['published', 'paused'].includes(event.status);

  return (
    <>
      <section className="card">
        <div className="row"><h1>{event.title}</h1><Status value={event.status} /></div>
        <p>{when(event.starts_at)} – {when(event.ends_at)} · {event.online_url ? 'Online' : event.venue}</p>
        <p>
          <Link to={`/events/${event.id}`}>Public page</Link> ·{' '}
          <Link to={`/organizer/events/${event.id}/attendees`}>Attendee list</Link>
          {live && <> · <Link to={`/organizer/events/${event.id}/edit?step=1`}>Edit details</Link> · <Link to={`/organizer/events/${event.id}/edit?step=2`}>Edit ticket types</Link></>}
        </p>
        {message && <p className="ok">{message}</p>}
        <ErrorMessage error={error} />
        <div className="row-left">
          {event.status === 'published' && <button type="button" className="secondary" onClick={() => act('pause')}>Pause sales</button>}
          {event.status === 'paused' && <button type="button" onClick={() => act('resume')}>Resume sales</button>}
        </div>
      </section>

      <section className="card">
        <h2>Ticket types</h2>
        <table>
          <thead><tr><th>Name</th><th>Price</th><th>Sold or held</th><th>Quantity</th><th>Sales</th></tr></thead>
          <tbody>
            {event.ticket_types.map((t) => (
              <tr key={t.id}>
                <td>{t.name}{t.visibility === 'hidden' && <span className="badge">Hidden</span>}</td>
                <td>{rwf(t.price)}</td><td>{t.sold}</td><td>{t.capacity}</td>
                <td>{t.on_sale ? 'On' : 'Stopped'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {live && (
        <section className="card danger">
          <h2>Cancel event</h2>
          <p>Stops all sales, releases unpaid reservations and refunds everyone who paid. This can't be undone and is recorded in the audit log.</p>
          <button type="button" className="danger" onClick={() => act('cancel', 'Cancel this event and refund all buyers? This cannot be undone.')}>Cancel event and refund buyers</button>
        </section>
      )}
    </>
  );
}
