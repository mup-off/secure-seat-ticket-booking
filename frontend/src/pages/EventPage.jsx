import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useApi } from '../useApi.js';
import { ErrorMessage } from '../components.jsx';
import { rwf, when } from '../format.js';

export default function EventPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: event, error: loadError } = useApi(`/events/${id}`);
  const [ticketTypeId, setTicketTypeId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [phone, setPhone] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  // One key per page view: if the form is submitted twice, the server makes one order.
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!event) return <p className="empty">Loading…</p>;

  const available = event.ticket_types.filter((t) => t.remaining > 0);
  const selected = ticketTypeId ?? available[0]?.id;

  async function buy(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // Only the ticket type and quantity are sent, never a price: the server reads
      // the price from the database and rejects any request that includes one.
      const order = await api.post('/checkout', {
        ticket_type_id: selected,
        quantity: Number(quantity),
        phone,
        idempotency_key: idempotencyKey,
      });
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <article className="card">
        <h1>{event.title}</h1>
        <p>{when(event.starts_at)} · {event.venue}</p>
        <p className="description">{event.description}</p>
      </article>

      <section className="card">
        <h2>Tickets</h2>
        {!event.ticket_types.length && <p className="empty">Tickets are not on sale yet.</p>}
        {!!event.ticket_types.length && !user && (
          <>
            <ul className="plain">
              {event.ticket_types.map((t) => <li key={t.id}>{t.name}: {rwf(t.price)}</li>)}
            </ul>
            <p><Link to="/login">Log in</Link> or <Link to="/register">sign up</Link> to buy tickets.</p>
          </>
        )}
        {!!event.ticket_types.length && user && user.role !== 'buyer' && (
          <p className="hint">Log in with a buyer account to buy tickets.</p>
        )}
        {!!event.ticket_types.length && user?.role === 'buyer' && (
          <form onSubmit={buy}>
            <ErrorMessage error={error} />
            <fieldset>
              <legend>Ticket type</legend>
              {event.ticket_types.map((t) => (
                <label key={t.id} className="radio">
                  <input type="radio" name="tt" value={t.id} disabled={t.remaining <= 0}
                    checked={selected === t.id} onChange={() => setTicketTypeId(t.id)} />
                  {t.name}: {rwf(t.price)}
                  <span className="hint">{t.remaining > 0 ? `${t.remaining} left` : 'Sold out'}</span>
                </label>
              ))}
            </fieldset>
            <label>Quantity
              <input type="number" min="1" max="10" value={quantity} required onChange={(e) => setQuantity(e.target.value)} />
            </label>
            <label>MTN or Airtel number to pay from
              <input type="tel" placeholder="0788123456" maxLength={20} value={phone} required autoComplete="tel"
                onChange={(e) => setPhone(e.target.value)} />
            </label>
            <p className="hint">You will get a prompt on your phone to approve the payment with your PIN. We never ask for your PIN.</p>
            <button type="submit" disabled={busy || !selected}>Reserve and pay</button>
          </form>
        )}
      </section>
    </>
  );
}
