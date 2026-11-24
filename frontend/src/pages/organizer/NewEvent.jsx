import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api.js';
import { ErrorMessage } from '../../components.jsx';

export default function NewEvent() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: '', venue: '', starts_at: '', description: '' });
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError(null);
    try {
      // <input type="datetime-local"> has no time zone: send it as Kigali time (UTC+2).
      const event = await api.post('/organizer/events', { ...form, starts_at: `${form.starts_at}:00+02:00` });
      navigate(`/organizer/events/${event.id}`);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section className="card narrow">
      <h1>New event</h1>
      <ErrorMessage error={error} />
      <form onSubmit={submit}>
        <label>Title <input required maxLength={120} value={form.title} onChange={set('title')} /></label>
        <label>Venue <input required maxLength={120} value={form.venue} onChange={set('venue')} /></label>
        <label>Starts (Kigali time) <input type="datetime-local" required value={form.starts_at} onChange={set('starts_at')} /></label>
        <label>Description <textarea required maxLength={5000} rows={6} value={form.description} onChange={set('description')} /></label>
        <button type="submit">Create event</button>
      </form>
    </section>
  );
}
