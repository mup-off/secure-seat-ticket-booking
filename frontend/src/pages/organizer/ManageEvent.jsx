import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../api.js';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { rwf, when } from '../../format.js';

export default function ManageEvent() {
  const { id } = useParams();
  const { data: event, error: loadError, reload } = useApi(`/organizer/events/${id}`);
  const [tt, setTt] = useState({ name: '', price: '', capacity: '' });
  const [error, setError] = useState(null);

  async function addTicketType(e) {
    e.preventDefault();
    setError(null);
    try {
      await api.post(`/organizer/events/${id}/ticket-types`, {
        name: tt.name, price: Number(tt.price), capacity: Number(tt.capacity),
      });
      setTt({ name: '', price: '', capacity: '' });
      await reload();
    } catch (err) {
      setError(err);
    }
  }

  async function cancel() {
    if (!window.confirm('Cancel this event? Ticket sales stop. This is recorded in the audit log.')) return;
    try {
      await api.post(`/organizer/events/${id}/cancel`);
      await reload();
    } catch (err) {
      setError(err);
    }
  }

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!event) return <p className="empty">Loading…</p>;

  return (
    <>
      <section className="card">
        <div className="row"><h1>{event.title}</h1><Status value={event.status} /></div>
        <p>{when(event.starts_at)} · {event.venue}</p>
        <p className="description">{event.description}</p>
        <p><Link to={`/events/${event.id}`}>Public page</Link> · <Link to={`/organizer/events/${event.id}/attendees`}>Attendee list</Link></p>
      </section>

      <section className="card">
        <h2>Ticket types</h2>
        {!!event.ticket_types.length && (
          <table>
            <thead><tr><th>Name</th><th>Price</th><th>Sold or held</th><th>Capacity</th></tr></thead>
            <tbody>
              {event.ticket_types.map((t) => (
                <tr key={t.id}><td>{t.name}</td><td>{rwf(t.price)}</td><td>{t.sold}</td><td>{t.capacity}</td></tr>
              ))}
            </tbody>
          </table>
        )}
        {event.status === 'active' && (
          <>
            <h3>Add a ticket type</h3>
            <p className="hint">The price can't be changed once the ticket type is created.</p>
            <ErrorMessage error={error} />
            <form onSubmit={addTicketType} className="grid">
              <label>Name <input required maxLength={60} placeholder="Regular" value={tt.name} onChange={(e) => setTt({ ...tt, name: e.target.value })} /></label>
              <label>Price (RWF) <input type="number" min="0" max="10000000" required value={tt.price} onChange={(e) => setTt({ ...tt, price: e.target.value })} /></label>
              <label>Number of tickets <input type="number" min="1" max="100000" required value={tt.capacity} onChange={(e) => setTt({ ...tt, capacity: e.target.value })} /></label>
              <button type="submit">Add</button>
            </form>
          </>
        )}
      </section>

      {event.status === 'active' && (
        <section className="card danger">
          <h2>Cancel event</h2>
          <p>Stops ticket sales. This is recorded in the audit log.</p>
          <button type="button" className="danger" onClick={cancel}>Cancel this event</button>
        </section>
      )}
    </>
  );
}
