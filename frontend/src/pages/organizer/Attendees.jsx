import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { rwf, when } from '../../format.js';

export default function Attendees() {
  const { id } = useParams();
  const { data, error } = useApi(`/organizer/events/${id}/attendees`);
  if (error) return <ErrorMessage error={error} />;
  if (!data) return <p className="empty">Loading…</p>;
  return (
    <>
      <h1>Attendees: {data.event.title}</h1>
      <p className="hint">Personal data. Use it only to run this event (Law No. 058/2021).</p>
      {!data.attendees.length ? (
        <p className="empty">No paid orders yet.</p>
      ) : (
        <table>
          <thead><tr><th>Buyer</th><th>Ticket type</th><th>Tickets</th><th>Price paid</th><th>Status</th><th>Checked in</th><th>Paid</th></tr></thead>
          <tbody>
            {data.attendees.map((a, i) => (
              <tr key={i}><td>{a.email}</td><td>{a.ticket_type}</td><td>{a.quantity}</td><td>{rwf(a.unit_price)}</td><td><Status value={a.status} /></td><td>{a.checked_in}</td><td>{when(a.paid_at)}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      <p><Link to={`/organizer/events/${id}`}>Back to event</Link></p>
    </>
  );
}
