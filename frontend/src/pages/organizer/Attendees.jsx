import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { rwf, when } from '../../format.js';
import { Icon, Skeleton } from '../../ui.jsx';

export default function Attendees() {
  const { id } = useParams();
  const { data, error } = useApi(`/organizer/events/${id}/attendees`);
  const [query, setQuery] = useState('');
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data?.attendees || []).filter((a) => !q || `${a.username} ${a.email} ${a.ticket_type}`.toLowerCase().includes(q));
  }, [data, query]);

  if (error) return <ErrorMessage error={error} />;
  if (!data) return <Skeleton height={240} />;
  const checkedIn = data.attendees.reduce((n, a) => n + a.checked_in, 0);
  const tickets = data.attendees.reduce((n, a) => n + (a.status === 'paid' ? a.quantity : 0), 0);

  return (
    <>
      <p><Link to={`/organizer/events/${id}`}>← Back to event</Link></p>
      <span className="eyebrow">{checkedIn} of {tickets} checked in</span>
      <h1>Attendees</h1>
      <p className="hint">{data.event.title}. Personal data: use it only to run this event (Law No. 058/2021).</p>
      <div className="filters">
        <label className="search" aria-label="Search attendees">
          <Icon name="search" />
          <input type="search" placeholder="Search by username, email or ticket type…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>
      {!data.attendees.length ? (
        <p className="empty">No paid orders yet.</p>
      ) : (
        <section className="card">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Buyer</th><th>Ticket type</th><th>Tickets</th><th>Price paid</th><th>Status</th><th>Checked in</th><th>Paid</th></tr></thead>
              <tbody>
                {rows.map((a, i) => (
                  <tr key={i}>
                    <td><strong>@{a.username}</strong><div className="hint">{a.email}</div></td>
                    <td>{a.ticket_type}</td><td>{a.quantity}</td><td>{rwf(a.unit_price)}</td>
                    <td><Status value={a.status} /></td><td>{a.checked_in} / {a.quantity}</td><td>{when(a.paid_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!rows.length && <p className="empty">No attendees match "{query}".</p>}
        </section>
      )}
    </>
  );
}
