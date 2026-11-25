// Step 1: event details. Every change is saved to the draft automatically, a moment
// after the organizer stops typing, so they can leave and come back at any time.
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { api } from '../../../api.js';
import { ErrorMessage } from '../../../components.jsx';
import { CATEGORIES, capitalize, fromKigaliInput, toKigaliInput } from '../../../format.js';

const DATE_FIELDS = ['starts_at', 'ends_at'];

function toForm(e) {
  return {
    title: e.title, description: e.description, category: e.category,
    mode: e.online_url ? 'online' : 'venue',
    venue: e.venue, venue_address: e.venue_address, online_url: e.online_url,
    starts_at: toKigaliInput(e.starts_at), ends_at: toKigaliInput(e.ends_at),
    contact_phone: e.contact_phone ? `0${e.contact_phone.slice(3)}` : '',
  };
}

function toApi(changes) {
  const out = {};
  for (const [k, v] of Object.entries(changes)) {
    if (k === 'mode') continue;
    out[k] = DATE_FIELDS.includes(k) ? fromKigaliInput(v) : v;
  }
  return out;
}

const StepDetails = forwardRef(function StepDetails({ event, onSaved }, ref) {
  const [form, setForm] = useState(() => toForm(event));
  const [saveState, setSaveState] = useState('saved');
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [coverError, setCoverError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const pending = useRef({});
  const timer = useRef(null);
  const editable = !['cancelled', 'ended'].includes(event.status);

  async function flush() {
    clearTimeout(timer.current);
    const changes = pending.current;
    pending.current = {};
    if (!Object.keys(toApi(changes)).length) return true;
    setSaveState('saving');
    try {
      const updated = await api.patch(`/organizer/events/${event.id}`, toApi(changes));
      onSaved(updated);
      setFieldErrors({});
      setError(null);
      setSaveState('saved');
      return true;
    } catch (err) {
      // Keep the unsaved changes so they are sent again with the next edit.
      pending.current = { ...changes, ...pending.current };
      const body = err.body && typeof err.body === 'object' ? err.body : {};
      const perField = Object.fromEntries(Object.entries(body).filter(([k]) => k in form).map(([k, v]) => [k, [].concat(v)[0]]));
      setFieldErrors(perField);
      setError(Object.keys(perField).length ? null : err);
      setSaveState('error');
      return false;
    }
  }

  // The wizard calls this before moving to another step.
  useImperativeHandle(ref, () => ({ flush }));
  useEffect(() => () => clearTimeout(timer.current), []);

  function change(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    pending.current[field] = value;
    setSaveState('unsaved');
    clearTimeout(timer.current);
    timer.current = setTimeout(flush, 800);
  }

  function setMode(mode) {
    setForm((f) => ({ ...f, mode }));
    // Switching to a venue clears the online link, and the other way round.
    if (mode === 'venue') change('online_url', '');
    else { change('venue', ''); change('venue_address', ''); }
  }

  async function uploadCover(e) {
    const file = e.target.files[0];
    e.target.value = '';
    await uploadFile(file);
  }

  function dropCover(e) {
    e.preventDefault();
    setDragging(false);
    if (editable) uploadFile(e.dataTransfer.files[0]);
  }

  async function uploadFile(file) {
    if (!file) return;
    setCoverError(null);
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return setCoverError(new Error('Use a JPEG, PNG or WebP picture.'));
    if (file.size > 5 * 1024 * 1024) return setCoverError(new Error('The image must be 5 MB or smaller.'));
    setUploading(true);
    try {
      await api.upload(`/organizer/events/${event.id}/cover`, file);
      onSaved(await api.get(`/organizer/events/${event.id}`));
    } catch (err) {
      setCoverError(err);
    } finally {
      setUploading(false);
    }
  }

  async function removeCover() {
    await api.del(`/organizer/events/${event.id}/cover`);
    onSaved(await api.get(`/organizer/events/${event.id}`));
  }

  const fe = (k) => fieldErrors[k] && <span className="field-error">{fieldErrors[k]}</span>;

  return (
    <section className="card">
      <div className="row">
        <h2>Event details</h2>
        <SaveIndicator state={saveState} />
      </div>
      {!editable && <p className="notice">This event is {event.status} and can no longer be changed.</p>}
      <ErrorMessage error={error} />
      <fieldset disabled={!editable} className="plain-fieldset">
        <label>Title {fe('title')}
          <input maxLength={120} value={form.title} onChange={(e) => change('title', e.target.value)} placeholder="Kigali Jazz Night" />
        </label>
        <label>Description {fe('description')}
          <textarea maxLength={5000} rows={6} value={form.description} onChange={(e) => change('description', e.target.value)} />
        </label>

        <div className="cover-field">
          <span className="label">Cover image (poster or flyer)</span>
          {event.cover_url && <img className="cover-thumb" src={event.cover_url} alt="Current cover" />}
          <label className={`dropzone ${dragging ? 'over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={dropCover}>
            <strong>{uploading ? 'Uploading…' : event.cover_url ? 'Drop a new image to replace it' : 'Drop your poster here'}</strong>
            <span>or click to choose a file · JPEG, PNG or WebP, up to 5 MB</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadCover} hidden />
          </label>
          {event.cover_url && <button type="button" className="link" onClick={removeCover}>Remove cover</button>}
          <ErrorMessage error={coverError} />
        </div>

        <label>Category {fe('category')}
          <select value={form.category} onChange={(e) => change('category', e.target.value)}>
            <option value="">Choose…</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{capitalize(c)}</option>)}
          </select>
        </label>

        <fieldset>
          <legend>Where</legend>
          <label className="radio"><input type="radio" checked={form.mode === 'venue'} onChange={() => setMode('venue')} /> At a venue</label>
          <label className="radio"><input type="radio" checked={form.mode === 'online'} onChange={() => setMode('online')} /> Online</label>
          {form.mode === 'venue' ? (
            <>
              <label>Venue name {fe('venue')}<input maxLength={120} value={form.venue} onChange={(e) => change('venue', e.target.value)} placeholder="Kigali Arena" /></label>
              <label>Address {fe('venue_address')}<input maxLength={200} value={form.venue_address} onChange={(e) => change('venue_address', e.target.value)} placeholder="KG 17 Ave, Kigali" /></label>
            </>
          ) : (
            <label>Online link {fe('online_url')}<input type="url" maxLength={300} value={form.online_url} onChange={(e) => change('online_url', e.target.value)} placeholder="https://…" /></label>
          )}
        </fieldset>

        <div className="grid-2">
          <label>Starts (Kigali time) {fe('starts_at')}
            <input type="datetime-local" value={form.starts_at} onChange={(e) => change('starts_at', e.target.value)} />
          </label>
          <label>Ends (Kigali time) {fe('ends_at')}
            <input type="datetime-local" value={form.ends_at} min={form.starts_at || undefined} onChange={(e) => change('ends_at', e.target.value)} />
          </label>
        </div>

        <label>Organizer contact phone {fe('contact_phone')}
          <input type="tel" maxLength={20} value={form.contact_phone} onChange={(e) => change('contact_phone', e.target.value)} placeholder="0788123456" />
        </label>
      </fieldset>
    </section>
  );
});

export function SaveIndicator({ state }) {
  const text = { saved: 'All changes saved', saving: 'Saving…', unsaved: 'Unsaved changes', error: 'Not saved: fix the highlighted field' }[state];
  return <span className={`save-state ${state}`}>{text}</span>;
}

export default StepDetails;
