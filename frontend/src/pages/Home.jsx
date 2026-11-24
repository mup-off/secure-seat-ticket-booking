import { Link } from 'react-router-dom';
import { useApi } from '../useApi.js';
import { ErrorMessage } from '../components.jsx';
import { rwf, when } from '../format.js';

export default function Home() {
  const { data: events, error } = useApi('/events');
  return (
    <>
      <h1>Upcoming events</h1>
      <ErrorMessage error={error} />
      {events && !events.length && <p className="empty">No events on sale yet.</p>}
      <ul className="events">
        {events?.map((e) => (
          <li key={e.id} className="card">
            <Link to={`/events/${e.id}`}><h2>{e.title}</h2></Link>
            <p>{when(e.starts_at)} · {e.venue}</p>
            {e.from_price !== null && <p className="price">From {rwf(e.from_price)}</p>}
          </li>
        ))}
      </ul>
    </>
  );
}
