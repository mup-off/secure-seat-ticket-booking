import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../useApi.js';
import { ErrorMessage } from '../components.jsx';
import { CATEGORIES, capitalize, rwf, when } from '../format.js';
import { CountUp, Icon, Skeleton, relativeDay } from '../ui.jsx';

function dateParts(iso) {
  const d = new Date(iso);
  const day = d.toLocaleString('en-GB', { timeZone: 'Africa/Kigali', day: 'numeric' });
  const month = d.toLocaleString('en-GB', { timeZone: 'Africa/Kigali', month: 'short' }).toUpperCase();
  return { day, month };
}

export default function Home() {
  const { data: events, error } = useApi('/events');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (events || []).filter((e) =>
      (category === 'all' || e.category === category) &&
      (!q || `${e.title} ${e.venue} ${e.category}`.toLowerCase().includes(q)));
  }, [events, query, category]);

  const present = useMemo(() => new Set((events || []).map((e) => e.category)), [events]);
  const thisWeek = (events || []).filter((e) => new Date(e.starts_at) - Date.now() < 7 * 86400000).length;

  return (
    <>
      <section className="hero">
        <span className="eyebrow">Kigali · live events</span>
        <h1>Your next <span className="glow">night out</span><br /><span className="outline">starts here.</span></h1>
        <p className="lead">Concerts, conferences, matches and Sunday services. Pay with mobile money in seconds; your ticket lands in your pocket.</p>
        {events && (
          <div className="hero-stats">
            <div><CountUp value={events.length} /><small>events on sale</small></div>
            <div><CountUp value={thisWeek} /><small>happening this week</small></div>
            <div><CountUp value={present.size} /><small>categories</small></div>
          </div>
        )}
      </section>

      <div className="filters">
        <label className="search" aria-label="Search events">
          <Icon name="search" />
          <input type="search" placeholder="Search by name, venue or category…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        <div className="chips" role="group" aria-label="Filter by category">
          {['all', ...CATEGORIES.filter((c) => present.has(c))].map((c) => (
            <button key={c} type="button" className={`chip ${category === c ? 'on' : ''}`} aria-pressed={category === c} onClick={() => setCategory(c)}>
              {c === 'all' ? 'All' : c}
            </button>
          ))}
        </div>
      </div>

      <ErrorMessage error={error} />
      {!events && !error && <div className="events"><Skeleton height={300} count={3} /></div>}
      {events && !shown.length && (
        <p className="empty">{events.length ? 'No events match your search.' : 'No events on sale yet. Check back soon!'}</p>
      )}

      <ul className="events">
        {shown.map((e, i) => {
          const { day, month } = dateParts(e.starts_at);
          const soon = relativeDay(e.starts_at);
          return (
            <li key={e.id} className="card event-card" style={{ '--i': i }}>
              <Link to={`/events/${e.id}`}>
                <div className="cover-box">
                  {e.cover_url ? <img className="card-cover" src={e.cover_url} alt="" loading="lazy" /> : <div className="card-cover placeholder" />}
                  <div className="date-stub"><b>{day}</b><small>{month}</small></div>
                </div>
                <div className="card-body">
                  {e.category && <span className="badge">{capitalize(e.category)}</span>}
                  {e.status === 'paused' && <span className="badge warn">Sales paused</span>}
                  {soon && <span className="badge gold">{soon}</span>}
                  <h2>{e.title}</h2>
                  <p className="meta">{when(e.starts_at)} · {e.online ? 'Online' : e.venue}</p>
                  <div className="foot">
                    <span className="price">{e.from_price === null ? '—' : e.from_price === 0 ? 'Free' : `From ${rwf(e.from_price)}`}</span>
                    <span className="soon">Get tickets →</span>
                  </div>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );
}
