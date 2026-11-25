import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useApi } from '../useApi.js';
import { ErrorMessage } from '../components.jsx';
import EventView from '../EventView.jsx';
import { rwf } from '../format.js';

export default function EventPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: event, error: loadError } = useApi(`/events/${id}`);
  const [unlocked, setUnlocked] = useState([]);
  const [code, setCode] = useState('');
  const [codeMessage, setCodeMessage] = useState(null);
  const [ticketTypeId, setTicketTypeId] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [phone, setPhone] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  // One key per page view: if the form is submitted twice, the server makes one order.
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!event) return <p className="empty">Loading…</p>;

  const shown = { ...event, ticket_types: [...event.ticket_types, ...unlocked] };
  const buyable = shown.ticket_types.filter((t) => t.sale_state === 'on_sale');
  const selected = buyable.find((t) => t.id === ticketTypeId) || buyable[0];
  const canBuy = event.status === 'published' && buyable.length > 0;

  async function unlock(e) {
    e.preventDefault();
    setCodeMessage(null);
    try {
      const res = await api.post(`/events/${id}/unlock`, { code });
      setUnlocked(res.ticket_types.filter((t) => !shown.ticket_types.some((s) => s.id === t.id)));
      setCodeMessage({ ok: true, text: 'Code accepted.' });
    } catch (err) {
      setCodeMessage({ ok: false, text: err.message });
    }
  }

  async function buy(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // Only the ticket type and quantity are sent, never a price: the server reads
      // the price from the database and rejects any request that includes one.
      const order = await api.post('/checkout', {
        ticket_type_id: selected.id,
        quantity: Number(quantity),
        phone,
        idempotency_key: idempotencyKey,
        ...(selected.hidden ? { access_code: code } : {}),
      });
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <EventView event={shown}>
      {event.status === 'published' && (
        <form onSubmit={unlock} className="inline-form">
          <label>Have an access code?
            <input value={code} maxLength={32} onChange={(e) => setCode(e.target.value)} placeholder="e.g. SPONSOR-2026" />
          </label>
          <button type="submit" className="secondary" disabled={!code}>Unlock</button>
          {codeMessage && <p className={codeMessage.ok ? 'ok' : 'error'}>{codeMessage.text}</p>}
        </form>
      )}

      {canBuy && !user && <p><Link to="/login">Log in</Link> or <Link to="/register">sign up</Link> to buy tickets.</p>}
      {canBuy && user && user.role !== 'buyer' && <p className="hint">Log in with a buyer account to buy tickets.</p>}
      {canBuy && user?.role === 'buyer' && (
        <form onSubmit={buy} className="buy-form">
          <h3>Buy tickets</h3>
          <ErrorMessage error={error} />
          <fieldset>
            <legend>Ticket type</legend>
            {buyable.map((t) => (
              <label key={t.id} className="radio">
                <input type="radio" name="tt" checked={selected?.id === t.id} onChange={() => setTicketTypeId(t.id)} />
                {t.name}: {rwf(t.price)}
              </label>
            ))}
          </fieldset>
          <label>Quantity (max {selected?.max_per_order})
            <input type="number" min="1" max={selected?.max_per_order} value={quantity} required onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label>MTN or Airtel number to pay from
            <input type="tel" placeholder="0788123456" maxLength={20} value={phone} required autoComplete="tel" onChange={(e) => setPhone(e.target.value)} />
          </label>
          <p className="hint">You will get a prompt on your phone to approve the payment with your PIN. We never ask for your PIN.</p>
          <button type="submit" disabled={busy || !selected}>Reserve and pay</button>
        </form>
      )}
    </EventView>
  );
}
