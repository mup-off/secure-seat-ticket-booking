// Three-step event set-up: details -> ticket types -> review and publish.
// The event is a draft on the server from the start, so every step is saved and the
// organizer can leave and continue later from "My events".
import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useApi } from '../../useApi.js';
import { ErrorMessage, Status } from '../../components.jsx';
import StepDetails from './wizard/StepDetails.jsx';
import StepTickets from './wizard/StepTickets.jsx';
import StepReview from './wizard/StepReview.jsx';

const STEPS = ['Event details', 'Ticket types', 'Review and publish'];

export default function EventWizard() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const step = Math.min(Math.max(Number(params.get('step')) || 1, 1), 3);
  const { data, error } = useApi(`/organizer/events/${id}`);
  const [event, setEvent] = useState(null);
  const detailsRef = useRef(null);

  useEffect(() => {
    if (data) setEvent(data);
  }, [data]);

  async function goTo(n) {
    // Save any pending details before leaving step 1.
    if (step === 1 && detailsRef.current && !(await detailsRef.current.flush())) return;
    setParams({ step: String(n) });
    window.scrollTo(0, 0);
  }

  if (error) return <ErrorMessage error={error} />;
  if (!event) return <p className="empty">Loading…</p>;
  const isDraft = event.status === 'draft';

  return (
    <>
      <div className="row">
        <h1>{event.title || 'New event'}</h1>
        <Status value={event.status} />
      </div>
      <p className="hint">
        {isDraft && 'Saved as a draft. You can leave and come back at any time. '}
        <Link to={isDraft ? '/organizer' : `/organizer/events/${id}`}>{isDraft ? 'Back to my events' : 'Back to event overview'}</Link>
      </p>

      <ol className="stepper">
        {STEPS.map((label, i) => (
          <li key={label} className={step === i + 1 ? 'active' : step > i + 1 ? 'done' : ''}>
            <button type="button" className="link" onClick={() => goTo(i + 1)}>{i + 1}. {label}</button>
          </li>
        ))}
      </ol>

      {step === 1 && <StepDetails ref={detailsRef} event={event} onSaved={setEvent} />}
      {step === 2 && <StepTickets event={event} onSaved={setEvent} />}
      {step === 3 && <StepReview event={event} onSaved={setEvent} goTo={goTo} />}

      <div className="row wizard-nav">
        {step > 1 ? <button type="button" className="secondary" onClick={() => goTo(step - 1)}>← Back</button> : <span />}
        {step < 3 && <button type="button" onClick={() => goTo(step + 1)}>Next: {STEPS[step]} →</button>}
      </div>
    </>
  );
}
