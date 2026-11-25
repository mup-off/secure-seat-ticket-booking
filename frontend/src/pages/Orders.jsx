import { Link } from 'react-router-dom';
import { useApi } from '../useApi.js';
import { ErrorMessage, Status } from '../components.jsx';
import { rwf, when } from '../format.js';
import { Skeleton } from '../ui.jsx';

export default function Orders() {
  const { data: orders, error } = useApi('/orders');
  const upcoming = (orders || []).filter((o) => o.status === 'paid' && new Date(o.event.starts_at) > Date.now());
  const rest = (orders || []).filter((o) => !upcoming.includes(o));
  return (
    <>
      <span className="eyebrow">Your wallet</span>
      <h1>My tickets</h1>
      <ErrorMessage error={error} />
      {!orders && !error && <Skeleton height={90} count={3} />}
      {orders && !orders.length && (
        <section className="card narrow">
          <h2>No tickets yet</h2>
          <p className="hint">Your next night out is a few taps away.</p>
          <Link className="button" to="/">Find an event</Link>
        </section>
      )}
      {!!upcoming.length && <h2>Coming up</h2>}
      <ul className="events">
        {upcoming.map((o, i) => (
          <li key={o.id} className="card event-card" style={{ '--i': i }}>
            <Link to={`/orders/${o.id}`}>
              <div className="card-body">
                <span className="badge gold">{o.quantity} ticket{o.quantity > 1 ? 's' : ''}</span>
                <h2>{o.event.title}</h2>
                <p className="meta">{when(o.event.starts_at)} · {o.event.venue || 'Online'}</p>
                <div className="foot"><span className="price">{rwf(o.total)}</span><span className="soon">Show tickets →</span></div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      {!!rest.length && (
        <section className="card" style={{ marginTop: 24 }}>
          <h2>History</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Event</th><th>Tickets</th><th>Total</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {rest.map((o) => (
                  <tr key={o.id}>
                    <td>{o.event.title}</td><td>{o.quantity}</td><td>{rwf(o.total)}</td>
                    <td><Status value={o.status} /></td><td><Link to={`/orders/${o.id}`}>View</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
