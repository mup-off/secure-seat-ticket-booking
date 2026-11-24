import { Link } from 'react-router-dom';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { when } from '../../format.js';

export default function Dashboard() {
  const { data: events, error } = useApi('/organizer/events');
  return (
    <>
      <div className="row">
        <h1>My events</h1>
        <Link className="button" to="/organizer/events/new">New event</Link>
      </div>
      <ErrorMessage error={error} />
      {events && !events.length && <p className="empty">You have no events yet.</p>}
      {!!events?.length && (
        <table>
          <thead><tr><th>Event</th><th>Date</th><th>Sold / capacity</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td>{when(e.starts_at)}</td>
                <td>{e.sold} / {e.capacity}</td>
                <td><Status value={e.status} /></td>
                <td><Link to={`/organizer/events/${e.id}`}>Manage</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
