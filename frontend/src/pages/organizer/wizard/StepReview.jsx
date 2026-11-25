// Step 3: the event page exactly as buyers will see it, then Publish.
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../../api.js';
import { ErrorMessage } from '../../../components.jsx';
import EventView from '../../../EventView.jsx';

export default function StepReview({ event, onSaved, goTo }) {
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/organizer/events/${event.id}/preview`).then(setPreview, setError);
  }, [event.id, event.updated_at, event.ticket_types]);

  async function publish() {
    setBusy(true);
    setError(null);
    try {
      onSaved(await api.post(`/organizer/events/${event.id}/publish`));
      navigate(`/organizer/events/${event.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const problems = event.publish_problems || [];
  const isDraft = event.status === 'draft';

  return (
    <>
      <section className="card">
        <h2>Review and publish</h2>
        {isDraft && problems.length > 0 && (
          <div className="notice">
            <strong>Before you can publish:</strong>
            <ul>
              {problems.map((p) => (
                <li key={p}>
                  {p}{' '}
                  <button type="button" className="link" onClick={() => goTo(/ticket|sales|hidden/i.test(p) ? 2 : 1)}>Fix</button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {isDraft && problems.length === 0 && <p className="ok">Everything is ready. Check the preview below, then publish.</p>}
        {!isDraft && <p className="hint">This event is already {event.status === 'published' ? 'on sale' : event.status}. Changes you save show on the event page straight away.</p>}
        {preview?.hidden_tiers?.length > 0 && (
          <p className="hint">Hidden ticket types not shown below (buyers need the code): {preview.hidden_tiers.join(', ')}.</p>
        )}
        <ErrorMessage error={error} />
        {isDraft && (
          <button type="button" onClick={publish} disabled={busy || problems.length > 0}>{busy ? 'Publishing…' : 'Publish event'}</button>
        )}
      </section>

      <p className="preview-label">Preview: what buyers will see</p>
      <div className="preview-frame">
        {preview ? (
          <EventView event={preview.page}>
            <p className="hint">Buyers will see the ticket form here.</p>
          </EventView>
        ) : (
          <p className="empty">Loading preview…</p>
        )}
      </div>
    </>
  );
}
