import { Link } from 'react-router-dom';
import { useApi } from '../useApi.js';
import { ErrorMessage, Status } from '../components.jsx';
import { rwf } from '../format.js';

export default function Orders() {
  const { data: orders, error } = useApi('/orders');
  return (
    <>
      <h1>My orders</h1>
      <ErrorMessage error={error} />
      {orders && !orders.length && <p className="empty">No orders yet. <Link to="/">Find an event</Link>.</p>}
      {!!orders?.length && (
        <table>
          <thead><tr><th>Event</th><th>Tickets</th><th>Total</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id}>
                <td>{o.event.title}</td>
                <td>{o.quantity}</td>
                <td>{rwf(o.total)}</td>
                <td><Status value={o.status} /></td>
                <td><Link to={`/orders/${o.id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
