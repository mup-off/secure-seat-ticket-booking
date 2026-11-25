import { Link } from 'react-router-dom';
import { useApi } from '../useApi.js';
import { ErrorMessage } from '../components.jsx';
import { capitalize, rwf, when } from '../format.js';

export default function Home() {
  const { data: events, error } = useApi('/events');
  return (
    <>
      <h1>Upcoming events</h1>
      <ErrorMessage error={error} />
      {events && !events.length && <p className="empty">No events on sale yet.</p>}
      <ul className="events">
        {events?.map((e) => (
          <li key={e.id} className="card event-card">
            <Link to={`/events/${e.id}`}>
              {e.cover_url ? <img className="card-cover" src={e.cover_url} alt="" /> : <div className="card-cover placeholder" />}
              {e.category && <span className="badge">{capitalize(e.category)}</span>}
              {e.status === 'paused' && <span className="badge warn">Sales paused</span>}
              <h2>{e.title}</h2>
            </Link>
            <p>{when(e.starts_at)} · {e.online ? 'Online' : e.venue}</p>
            {e.from_price !== null && <p className="price">{e.from_price === 0 ? 'Free' : `From ${rwf(e.from_price)}`}</p>}
          </li>
        ))}
      </ul>
    </>
  );
}
