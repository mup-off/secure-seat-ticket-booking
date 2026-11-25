import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';
import { useApi } from '../useApi.js';
import { useToast } from '../toast.jsx';
import { ErrorMessage } from '../components.jsx';
import EventView from '../EventView.jsx';
import { rwf } from '../format.js';
import { Skeleton } from '../ui.jsx';

export default function EventPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const toast = useToast();
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
  const [bump, setBump] = useState(false);
  const totalRef = useRef(null);
  // One key per page view: if the form is submitted twice, the server makes one order.
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);

  const shown = event && { ...event, ticket_types: [...event.ticket_types, ...unlocked] };
  const buyable = shown ? shown.ticket_types.filter((t) => t.sale_state === 'on_sale') : [];
  const selected = buyable.find((t) => t.id === ticketTypeId) || buyable[0];
  const maxQty = selected ? Math.min(selected.max_per_order, selected.remaining) : 1;
  const total = selected ? selected.price * quantity : 0;

  // Keep the quantity within what this tier allows, and make the total "bump" when it changes.
  useEffect(() => { if (quantity > maxQty) setQuantity(Math.max(1, maxQty)); }, [maxQty, quantity]);
  useEffect(() => {
    setBump(true);
    const t = setTimeout(() => setBump(false), 350);
    return () => clearTimeout(t);
  }, [total]);

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!shown) return <><Skeleton height={300} /><Skeleton height={160} count={2} /></>;

  const canBuy = event.status === 'published' && buyable.length > 0;

  async function unlock(e) {
    e.preventDefault();
    setCodeMessage(null);
    try {
      const res = await api.post(`/events/${id}/unlock`, { code });
      const fresh = res.ticket_types.filter((t) => !shown.ticket_types.some((s) => s.id === t.id));
      setUnlocked([...unlocked, ...fresh]);
      if (fresh[0]) setTicketTypeId(fresh[0].id);
      toast(`Unlocked: ${res.ticket_types.map((t) => t.name).join(', ')}`);
    } catch (err) {
      setCodeMessage(err.message);
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
        quantity,
        phone,
        idempotency_key: idempotencyKey,
        ...(selected.hidden ? { access_code: code } : {}),
      });
      toast(total === 0 ? 'Your free tickets are ready!' : 'Seats held! Approve the payment on your phone.');
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <EventView event={shown} selectedId={canBuy ? selected?.id : undefined} onSelect={canBuy ? setTicketTypeId : undefined}>
      <section className="card checkout">
        <span className="eyebrow">Checkout</span>
        <h2>Get tickets</h2>

        {!canBuy && <p className="hint">{event.status === 'paused' ? 'Sales are paused for now. Check back soon.' : 'Tickets are not available right now.'}</p>}
        {canBuy && !user && (
          <>
            <p className="hint">Pick your tickets on the left, then log in to pay.</p>
            <Link className="button big" to="/login">Log in to buy</Link>{' '}
            <Link to="/register">or create an account</Link>
          </>
        )}
        {canBuy && user && user.role !== 'buyer' && <p className="hint">Log in with a buyer account to buy tickets.</p>}
        {canBuy && user?.role === 'buyer' && (
          <form onSubmit={buy}>
            <ErrorMessage error={error} />
            <p className="hint">Selected: <strong>{selected.name}</strong> · {rwf(selected.price)} each</p>
            <span className="label">Quantity</span>
            <div className="stepper-qty">
              <button type="button" onClick={() => setQuantity(Math.max(1, quantity - 1))} disabled={quantity <= 1} aria-label="One less">−</button>
              <output aria-live="polite">{quantity}</output>
              <button type="button" onClick={() => setQuantity(Math.min(maxQty, quantity + 1))} disabled={quantity >= maxQty} aria-label="One more">+</button>
            </div>
            <p className="hint">Up to {selected.max_per_order} per order.</p>
            <label>MTN or Airtel number to pay from
              <input type="tel" placeholder="0788 123 456" maxLength={20} value={phone} required autoComplete="tel" inputMode="tel" onChange={(e) => setPhone(e.target.value)} />
            </label>
            <div className="total">
              <span>Total</span>
              <strong ref={totalRef} className={bump ? 'bump' : ''}>{rwf(total)}</strong>
            </div>
            <button type="submit" className="big" style={{ width: '100%' }} disabled={busy || !selected}>
              {busy ? 'Holding your seats…' : total === 0 ? 'Get free tickets' : `Pay ${rwf(total)}`}
            </button>
            <p className="hint">You'll get a prompt on your phone to approve with your PIN. We never ask for your PIN. Seats are held for 10 minutes.</p>
          </form>
        )}

        {event.status === 'published' && (
          <form onSubmit={unlock} className="inline-form">
            <label>Have an access code?
              <input value={code} maxLength={32} onChange={(e) => setCode(e.target.value)} placeholder="e.g. SPONSOR-2026" />
            </label>
            <button type="submit" className="secondary" disabled={!code}>Unlock</button>
            {codeMessage && <p className="error">{codeMessage}</p>}
          </form>
        )}
      </section>
    </EventView>
  );
}
