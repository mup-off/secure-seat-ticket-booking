// The event page as buyers see it. Used by the real event page AND by the
// organizer's "Review and publish" step, so the preview is exactly what buyers get.
import { capitalize, rwf, when } from './format.js';

const SALE_STATE_TEXT = {
  on_sale: null,
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

export function TierLine({ tier }) {
  const state = SALE_STATE_TEXT[tier.sale_state];
  return (
    <div className="tier-line">
      <div>
        <strong>{tier.name}</strong>
        {tier.hidden && <span className="badge">Access code</span>}
        {tier.description && <div className="hint">{tier.description}</div>}
        {tier.sale_state === 'not_started' && tier.sales_start && <div className="hint">On sale from {when(tier.sales_start)}</div>}
        {tier.sale_state === 'on_sale' && tier.sales_end && <div className="hint">Sales end {when(tier.sales_end)}</div>}
      </div>
      <div className="tier-price">
        {rwf(tier.price)}
        <div className="hint">{state || `${tier.remaining} left`}</div>
      </div>
    </div>
  );
}

export default function EventView({ event, children }) {
  const link = safeHttpsUrl(event.online_url);
  return (
    <>
      <article className="card event-page">
        {event.cover_url && <img className="cover" src={event.cover_url} alt="" />}
        {event.status === 'paused' && <p className="notice">Ticket sales are paused for now.</p>}
        {event.status === 'cancelled' && <p className="error">This event has been cancelled. Paid orders are being refunded.</p>}
        {event.status === 'ended' && <p className="notice">This event has ended.</p>}
        {event.category && <span className="badge">{capitalize(event.category)}</span>}
        <h1>{event.title || <span className="empty">Untitled event</span>}</h1>
        <p className="when">
          {when(event.starts_at)}{event.ends_at && ` – ${when(event.ends_at)}`}
          <span className="hint"> (Kigali time)</span>
        </p>
        {link ? (
          <p>Online: <a href={link} target="_blank" rel="noopener noreferrer">{link}</a></p>
        ) : (
          <p>{event.venue}{event.venue_address && `, ${event.venue_address}`}</p>
        )}
        {event.contact_phone && <p className="hint">Organizer contact: +{event.contact_phone}</p>}
        <p className="description">{event.description}</p>
      </article>

      <section className="card">
        <h2>Tickets</h2>
        {!event.ticket_types.length && <p className="empty">Tickets are not on sale yet.</p>}
        {event.ticket_types.map((t) => <TierLine key={t.id} tier={t} />)}
        {children}
      </section>
    </>
  );
}
