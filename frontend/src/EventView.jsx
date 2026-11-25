// The event page as buyers see it. Used by the real event page AND by the
// organizer's "Review and publish" step, so the preview is exactly what buyers get.
import { capitalize, rwf, when } from './format.js';
import { Countdown, Icon } from './ui.jsx';

const SALE_STATE_TEXT = {
  not_started: 'Sales not started',
  ended: 'Sales ended',
  sold_out: 'Sold out',
  stopped: 'Not on sale',
};

function safeHttpsUrl(url) {
  // The server only accepts https:// links; checked again here before making a link.
  try {
    const u = new URL(url);
    return u.protocol === 'https:' ? u.href : null;
  } catch {
    return null;
  }
}

function TierContent({ tier }) {
  const state = SALE_STATE_TEXT[tier.sale_state];
  const low = tier.sale_state === 'on_sale' && tier.remaining <= 10;
  return (
    <>
      <div>
        <strong>{tier.name}</strong>{' '}
        {tier.hidden && <span className="badge gold">Unlocked</span>}
        {low && <span className="badge hot">Only {tier.remaining} left</span>}
        {tier.description && <div className="hint">{tier.description}</div>}
        {tier.sale_state === 'not_started' && tier.sales_start && <div className="hint">On sale from {when(tier.sales_start)}</div>}
        {tier.sale_state === 'on_sale' && tier.sales_end && <div className="hint">Sales end {when(tier.sales_end)}</div>}
        {state && <div className="hint">{state}</div>}
      </div>
      <div className="tier-price">{rwf(tier.price)}</div>
    </>
  );
}

export function TierList({ tiers, selectedId, onSelect }) {
  return (
    <div className="tiers" role={onSelect ? 'radiogroup' : undefined} aria-label="Ticket types">
      {tiers.map((t) => {
        const available = t.sale_state === 'on_sale';
        const cls = `tier ${selectedId === t.id ? 'selected' : ''} ${available ? '' : 'unavailable'}`;
        return onSelect ? (
          <button key={t.id} type="button" className={cls} role="radio" aria-checked={selectedId === t.id}
            disabled={!available} onClick={() => onSelect(t.id)}>
            <TierContent tier={t} />
          </button>
        ) : (
          <div key={t.id} className={cls}><TierContent tier={t} /></div>
        );
      })}
    </div>
  );
}

export default function EventView({ event, selectedId, onSelect, children }) {
  const link = safeHttpsUrl(event.online_url);
  const totalLeft = event.ticket_types.reduce((n, t) => n + (t.sale_state === 'on_sale' ? t.remaining : 0), 0);
  return (
    <>
      <section className="event-hero">
        {event.cover_url ? <img className="backdrop" src={event.cover_url} alt="" /> : <div className="backdrop placeholder" />}
        <div className="hero-text">
          {event.category && <span className="badge gold">{capitalize(event.category)}</span>}
          {event.status === 'paused' && <span className="badge warn">Sales paused</span>}
          {event.status === 'cancelled' && <span className="badge hot">Cancelled</span>}
          {event.status === 'ended' && <span className="badge">Ended</span>}
          <h1>{event.title || 'Untitled event'}</h1>
          <div className="facts">
            <span><Icon name="calendar" />{when(event.starts_at) || 'Date to be announced'}</span>
            {link ? <span><Icon name="globe" />Online event</span> : event.venue && <span><Icon name="pin" />{event.venue}</span>}
          </div>
        </div>
      </section>

      <div className="event-layout">
        <div>
          {['published', 'paused'].includes(event.status) && (
            <section className="card"><Countdown to={event.starts_at} label="Doors open in" /></section>
          )}
          {event.status === 'cancelled' && <p className="error">This event has been cancelled. Everyone who paid is being refunded.</p>}

          <section className="card">
            <h2>About</h2>
            <p className="description">{event.description}</p>
            <div className="facts">
              <span><Icon name="clock" />{when(event.starts_at)}{event.ends_at && ` – ${when(event.ends_at)}`} (Kigali)</span>
            </div>
            <div className="facts">
              {link ? (
                <span><Icon name="globe" /><a href={link} target="_blank" rel="noopener noreferrer">{link}</a></span>
              ) : (
                <span><Icon name="pin" />{event.venue}{event.venue_address && `, ${event.venue_address}`}</span>
              )}
              {event.contact_phone && <span><Icon name="phone" />+{event.contact_phone}</span>}
            </div>
          </section>

          <section className="card">
            <div className="row">
              <h2>Tickets</h2>
              {totalLeft > 0 && <span className="hint">{totalLeft.toLocaleString('en-US')} available</span>}
            </div>
            {!event.ticket_types.length && <p className="empty">Tickets are not on sale yet.</p>}
            <TierList tiers={event.ticket_types} selectedId={selectedId} onSelect={onSelect} />
          </section>
        </div>
        <aside>{children}</aside>
      </div>
    </>
  );
}
