import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useApi } from '../useApi.js';
import { useToast } from '../toast.jsx';
import { ErrorMessage, Status } from '../components.jsx';
import { rwf, when } from '../format.js';
import { Confetti, QrImage, Skeleton, copyText, useNow } from '../ui.jsx';

const HOLD_SECONDS = 10 * 60;

function HoldRing({ expiresAt }) {
  const now = useNow();
  const left = Math.max(0, Math.round((new Date(expiresAt).getTime() - now) / 1000));
  const r = 46;
  const c = 2 * Math.PI * r;
  const frac = Math.min(left / HOLD_SECONDS, 1);
  return (
    <div className={`ring ${left < 60 ? 'urgent' : ''}`} role="timer" aria-label={`${Math.floor(left / 60)} minutes ${left % 60} seconds left`}>
      <svg width="110" height="110" viewBox="0 0 110 110" aria-hidden="true">
        <circle className="track" cx="55" cy="55" r={r} />
        <circle className="arc" cx="55" cy="55" r={r} strokeDasharray={c} strokeDashoffset={c * (1 - frac)} />
      </svg>
      <b>{Math.floor(left / 60)}:{String(left % 60).padStart(2, '0')}</b>
    </div>
  );
}

function TicketStub({ order, ticket, index }) {
  const toast = useToast();
  return (
    <article className={`ticket ${ticket.checked_in_at ? 'used' : ''}`} style={{ '--i': index }}>
      <div className="main">
        <span className="eyebrow">Admit one · ticket {index + 1} of {order.quantity}</span>
        <h3>{order.event.title}</h3>
        <dl>
          <div><dt>Date</dt><dd>{when(order.event.starts_at)}</dd></div>
          <div><dt>Where</dt><dd>{order.event.venue || 'Online'}</dd></div>
          <div><dt>Type</dt><dd>{order.ticket_type}</dd></div>
        </dl>
        <div className="code">{ticket.token}</div>
        {ticket.checked_in_at && <p className="hint">Checked in {when(ticket.checked_in_at)}</p>}
        <div className="zigzag" />
      </div>
      <div className="stub">
        <QrImage value={ticket.token} size={140} alt={`QR code for ticket ${index + 1}`} />
        <button type="button" onClick={async () => toast((await copyText(ticket.token)) ? 'Ticket code copied' : 'Could not copy. Select the code instead.', 'info')}>
          Copy code
        </button>
      </div>
    </article>
  );
}

export default function OrderPage() {
  const { id } = useParams();
  const toast = useToast();
  const { data: order, error: loadError, reload } = useApi(`/orders/${id}`);
  const [error, setError] = useState(null);
  const [celebrate, setCelebrate] = useState(false);
  const lastStatus = useRef(null);

  // While the payment is pending, ask the provider every 5 seconds, so the page
  // updates by itself as soon as the buyer approves on their phone.
  useEffect(() => {
    if (order?.status !== 'pending') return undefined;
    const t = setInterval(async () => {
      try { await api.post(`/orders/${id}/refresh`); await reload(); } catch { /* next tick retries */ }
    }, 5000);
    return () => clearInterval(t);
  }, [order?.status, id, reload]);

  useEffect(() => {
    if (!order) return;
    if (lastStatus.current === 'pending' && order.status === 'paid') {
      setCelebrate(true);
      toast("Payment confirmed. You're going!");
    }
    if (lastStatus.current === null && order.status === 'paid' && Date.now() - new Date(order.paid_at).getTime() < 15000) {
      setCelebrate(true); // free tickets, or just paid on the previous page
    }
    lastStatus.current = order.status;
  }, [order, toast]);

  async function act(path, body) {
    setError(null);
    try {
      await api.post(path, body);
      await reload();
    } catch (err) {
      setError(err);
    }
  }

  if (loadError) return <ErrorMessage error={loadError} />;
  if (!order) return <><Skeleton height={160} /><Skeleton height={200} /></>;

  return (
    <>
      {celebrate && <Confetti />}
      <p><Link to="/orders">← My tickets</Link></p>
      <section className="card">
        <div className="row">
          <div>
            <span className="eyebrow">Order #{order.id}</span>
            <h1>{order.event.title}</h1>
          </div>
          <Status value={order.status} />
        </div>
        <p className="hint">{when(order.event.starts_at)} · {order.event.venue || 'Online'}</p>
        <p>{order.quantity} × {order.ticket_type} at {rwf(order.unit_price)} = <strong>{rwf(order.total)}</strong></p>
        <ErrorMessage error={error} />

        {order.status === 'pending' && (
          <div className="hold">
            <HoldRing expiresAt={order.expires_at} />
            <div>
              <p><span className="phone-pulse" />A payment prompt was sent to your phone. Approve it with your PIN.</p>
              <p className="hint">This page updates by itself. Your seats are held until {when(order.expires_at)}.</p>
              <button type="button" className="secondary" onClick={() => act(`/orders/${order.id}/refresh`)}>Check now</button>
            </div>
          </div>
        )}
        {order.status === 'pending' && order.dev_payments && (
          <div className="dev">
            <p><strong>Development only:</strong> no real phone gets the prompt. Act as the buyer's phone:</p>
            <div className="row-left">
              <button type="button" onClick={() => act(`/dev/orders/${order.id}/pay`, { decision: 'approve' })}>Approve payment</button>
              <button type="button" className="secondary" onClick={() => act(`/dev/orders/${order.id}/pay`, { decision: 'decline' })}>Decline</button>
            </div>
          </div>
        )}
        {order.status === 'expired' && <p className="notice">The hold ran out before the payment was confirmed, so the seats were released. <Link to={`/events/${order.event.id}`}>Try again</Link></p>}
        {order.status === 'failed' && <p className="notice">The payment was declined or failed, or the event was cancelled before you paid. No money was taken.</p>}
        {order.status === 'refund_pending' && <p className="notice">This event was cancelled. Your refund of {rwf(order.total)} is on its way to your mobile money account.</p>}
        {order.status === 'refunded' && <p className="ok">This event was cancelled and {rwf(order.total)} has been refunded to your mobile money account.</p>}
      </section>

      {!!order.tickets?.length && (
        <section>
          <div className="row">
            <h2>Your tickets</h2>
            <span className="hint">Show the QR code at the gate. Each one works once, so don't share it.</span>
          </div>
          {order.tickets.map((t, i) => <TicketStub key={t.id} order={order} ticket={t} index={i} />)}
        </section>
      )}
    </>
  );
}
