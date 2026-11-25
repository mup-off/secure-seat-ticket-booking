import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../api.js';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { when } from '../../format.js';

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: events, error } = useApi('/organizer/events');
  const [createError, setCreateError] = useState(null);

  async function startNew() {
    setCreateError(null);
    try {
      // The draft exists on the server from the first click, so nothing is ever lost.
      const draft = await api.post('/organizer/events', {});
      navigate(`/organizer/events/${draft.id}/edit?step=1`);
    } catch (err) {
      setCreateError(err);
    }
  }

  return (
    <>
      <div className="row">
        <h1>My events</h1>
        <button type="button" onClick={startNew}>+ New event</button>
      </div>
      <ErrorMessage error={error || createError} />
      {events && !events.length && <p className="empty">You have no events yet. Click "New event" to set one up in three short steps.</p>}
      {!!events?.length && (
        <table>
          <thead><tr><th>Event</th><th>Date</th><th>Sold / quantity</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.title || <span className="empty">Untitled draft</span>}</td>
                <td>{when(e.starts_at) || '—'}</td>
                <td>{e.sold} / {e.capacity}</td>
                <td><Status value={e.status} /></td>
                <td>
                  {e.status === 'draft'
                    ? <Link to={`/organizer/events/${e.id}/edit`}>Continue editing</Link>
                    : <Link to={`/organizer/events/${e.id}`}>Manage</Link>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
