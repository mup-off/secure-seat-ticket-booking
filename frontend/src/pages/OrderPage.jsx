import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useApi } from '../useApi.js';
import { ErrorMessage, Status } from '../components.jsx';
import { rwf, when } from '../format.js';

export default function OrderPage() {
  const { id } = useParams();
  const { data: order, error: loadError, reload } = useApi(`/orders/${id}`);
  const [error, setError] = useState(null);

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
  if (!order) return <p className="empty">Loading…</p>;

  return (
    <>
      <section className="card">
        <h1>Order #{order.id}</h1>
        <p><strong>{order.event.title}</strong> · {when(order.event.starts_at)} · {order.event.venue}</p>
        <p>{order.quantity} × {order.ticket_type} at {rwf(order.unit_price)} = <strong>{rwf(order.total)}</strong></p>
        <p>Status: <Status value={order.status} /></p>
        <ErrorMessage error={error} />

        {order.status === 'pending' && (
          <>
            <p>Approve the payment prompt on your phone. Your tickets are held until <strong>{when(order.expires_at)}</strong>.</p>
            <button type="button" onClick={() => act(`/orders/${order.id}/refresh`)}>I have approved it, check again</button>
            {order.dev_payments && (
              <div className="dev">
                <p><strong>Development only:</strong> no real phone receives the prompt. Act as the buyer's phone:</p>
                <button type="button" onClick={() => act(`/dev/orders/${order.id}/pay`, { decision: 'approve' })}>Approve payment</button>{' '}
                <button type="button" className="secondary" onClick={() => act(`/dev/orders/${order.id}/pay`, { decision: 'decline' })}>Decline</button>
              </div>
            )}
          </>
        )}
        {order.status === 'expired' && <p>The hold ran out before the payment was confirmed, so the tickets were released.</p>}
        {order.status === 'failed' && <p>The payment was declined or failed, or the event was cancelled before you paid. No money was taken.</p>}
        {order.status === 'refund_pending' && <p>This event was cancelled. Your refund of {rwf(order.total)} is being sent back to your mobile money account.</p>}
        {order.status === 'refunded' && <p>This event was cancelled and {rwf(order.total)} has been refunded to your mobile money account.</p>}
      </section>

      {!!order.tickets?.length && (
        <section className="card">
          <h2>Your tickets</h2>
          <p className="hint">Show the ticket code at the gate. Each code works once, so don't share it.</p>
          <ol className="tickets">
            {order.tickets.map((t) => (
              <li key={t.id}><code>{t.token}</code>{t.checked_in_at && ` · used ${when(t.checked_in_at)}`}</li>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}
