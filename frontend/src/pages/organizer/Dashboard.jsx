import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../api.js';
import { useAuth } from '../../auth.jsx';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import { when } from '../../format.js';
import { Bar, CountUp, Skeleton } from '../../ui.jsx';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: events, error } = useApi('/organizer/events');
  const [createError, setCreateError] = useState(null);
  const [creating, setCreating] = useState(false);

  async function startNew() {
    setCreateError(null);
    setCreating(true);
    try {
      // The draft exists on the server from the first click, so nothing is ever lost.
      const draft = await api.post('/organizer/events', {});
      navigate(`/organizer/events/${draft.id}/edit?step=1`);
    } catch (err) {
      setCreateError(err);
      setCreating(false);
    }
  }

  const live = (events || []).filter((e) => ['published', 'paused'].includes(e.status));
  const sold = (events || []).reduce((n, e) => n + (['published', 'paused', 'ended'].includes(e.status) ? e.sold : 0), 0);
  const drafts = (events || []).filter((e) => e.status === 'draft').length;

  return (
    <>
      <div className="row">
        <div>
          <span className="eyebrow">Organizer · @{user?.username}</span>
          <h1>My events</h1>
        </div>
        <button type="button" className="big" onClick={startNew} disabled={creating}>{creating ? 'Opening…' : '+ New event'}</button>
      </div>
      <ErrorMessage error={error || createError} />

      {events && (
        <div className="stats">
          <div className="stat" style={{ '--i': 0 }}><b><CountUp value={live.length} /></b><small>Events on sale</small></div>
          <div className="stat" style={{ '--i': 1 }}><b><CountUp value={sold} /></b><small>Tickets sold or held</small></div>
          <div className="stat" style={{ '--i': 2 }}><b><CountUp value={drafts} /></b><small>Drafts in progress</small></div>
        </div>
      )}

      {!events && !error && <Skeleton height={70} count={3} />}
      {events && !events.length && (
        <section className="card narrow">
          <h2>Your stage is empty</h2>
          <p className="hint">Set up your first event in three short steps: details, ticket types, then review and publish. It's saved as a draft the whole time.</p>
          <button type="button" onClick={startNew}>+ Create my first event</button>
        </section>
      )}
      {!!events?.length && (
        <section className="card">
          <div className="table-wrap">
            <table>
              <thead><tr><th>Event</th><th>Date</th><th>Sales</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td><strong>{e.title || <span className="empty">Untitled draft</span>}</strong></td>
                    <td>{when(e.starts_at) || '—'}</td>
                    <td style={{ minWidth: 150 }}>
                      <span className="hint">{e.sold} / {e.capacity}</span>
                      {e.capacity > 0 && <Bar value={e.sold} max={e.capacity} low={-1} />}
                    </td>
                    <td><Status value={e.status} /></td>
                    <td>
                      {e.status === 'draft'
                        ? <Link to={`/organizer/events/${e.id}/edit`}>Continue →</Link>
                        : <Link to={`/organizer/events/${e.id}`}>Manage →</Link>}
                    </td>
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
