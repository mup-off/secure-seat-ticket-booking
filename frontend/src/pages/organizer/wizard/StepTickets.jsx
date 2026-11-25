// Step 2: ticket types. Each tier is saved with its own button. Tiers can be dragged
// (or moved with the arrow buttons) into the order buyers will see.
import { useState } from 'react';
import { api } from '../../../api.js';
import { ErrorMessage } from '../../../components.jsx';
import { fromKigaliInput, rwf, toKigaliInput } from '../../../format.js';
import { useToast } from '../../../toast.jsx';
import { Bar } from '../../../ui.jsx';

const EMPTY = {
  name: '', description: '', price: '', capacity: '', max_per_order: 10,
  sales_start: '', sales_end: '', visibility: 'public', access_code: '', on_sale: true,
};

function toForm(t) {
  return {
    name: t.name, description: t.description, price: String(t.price), capacity: String(t.capacity),
    max_per_order: t.max_per_order, sales_start: toKigaliInput(t.sales_start), sales_end: toKigaliInput(t.sales_end),
    visibility: t.visibility, access_code: '', on_sale: t.on_sale,
  };
}

function toApi(f) {
  const body = {
    name: f.name, description: f.description, price: Number(f.price), capacity: Number(f.capacity),
    max_per_order: Number(f.max_per_order), sales_start: fromKigaliInput(f.sales_start),
    sales_end: fromKigaliInput(f.sales_end), visibility: f.visibility, on_sale: f.on_sale,
  };
  if (f.visibility === 'hidden' && f.access_code) body.access_code = f.access_code;
  return body;
}

function TierCard({ event, tier, editable, onSaved, onCancelNew, dragProps, onMove, index, count, dragOver }) {
  const toast = useToast();
  const [form, setForm] = useState(tier ? toForm(tier) : EMPTY);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(!tier);
  const set = (k) => (e) => {
    setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
    setDirty(true);
  };

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const base = `/organizer/events/${event.id}/ticket-types`;
      const updated = tier ? await api.patch(`${base}/${tier.id}`, toApi(form)) : await api.post(base, toApi(form));
      setDirty(false);
      toast(tier ? `Saved "${form.name}"` : `Added "${form.name}"`);
      onSaved(updated);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete the "${tier.name}" ticket type?`)) return;
    try {
      onSaved(await api.del(`/organizer/events/${event.id}/ticket-types/${tier.id}`));
      toast(`Deleted "${tier.name}"`, 'info');
    } catch (err) {
      setError(err);
    }
  }

  return (
    <form className={`card tier-card ${tier ? '' : 'new'} ${dragOver ? 'drag-over' : ''}`} onSubmit={save} {...(tier && editable ? dragProps.drop : {})}>
      <div className="row">
        <div className="row-left">
          {tier && editable && (
            <>
              <span className="drag-handle" title="Drag to reorder" aria-hidden="true" {...dragProps.handle}>⠿</span>
              <button type="button" className="icon" onClick={() => onMove(index, -1)} disabled={index === 0} aria-label="Move up">↑</button>
              <button type="button" className="icon" onClick={() => onMove(index, 1)} disabled={index === count - 1} aria-label="Move down">↓</button>
            </>
          )}
          <h3>{tier ? tier.name : 'New ticket type'}</h3>
          {tier && <span className="hint">{rwf(tier.price)} · {tier.sold} sold or held of {tier.capacity}</span>}
        </div>
        {tier && !tier.on_sale && <span className="status paused">Sales stopped</span>}
      </div>
      {tier && <Bar value={tier.sold} max={tier.capacity} low={-1} />}
      <ErrorMessage error={error} />
      <fieldset disabled={!editable} className="plain-fieldset">
        <div className="grid-3">
          <label>Name<input required maxLength={60} value={form.name} onChange={set('name')} placeholder="Regular, VIP, Early bird" /></label>
          <label>Price (RWF, 0 = free)<input type="number" required min="0" max="10000000" step="1" value={form.price} onChange={set('price')} /></label>
          <label>Quantity<input type="number" required min={Math.max(1, tier?.sold || 0)} max="100000" value={form.capacity} onChange={set('capacity')} /></label>
        </div>
        {tier?.sold > 0 && <p className="hint">{tier.sold} already sold or held, so the quantity can't go below that. Price changes apply to new orders only.</p>}
        <div className="grid-3">
          <label>Sales start (Kigali)<input type="datetime-local" value={form.sales_start} onChange={set('sales_start')} /></label>
          <label>Sales end (Kigali)<input type="datetime-local" value={form.sales_end} onChange={set('sales_end')} /></label>
          <label>Max per order<input type="number" required min="1" max="50" value={form.max_per_order} onChange={set('max_per_order')} /></label>
        </div>
        <p className="hint">Leave sales start empty to sell as soon as the event is published, and sales end empty to sell until the event ends.</p>
        <label>Description<input maxLength={300} value={form.description} onChange={set('description')} placeholder="Includes front seating" /></label>
        <div className="grid-2">
          <label>Visibility
            <select value={form.visibility} onChange={set('visibility')}>
              <option value="public">Public: everyone sees it</option>
              <option value="hidden">Hidden: unlocked with a code</option>
            </select>
          </label>
          {form.visibility === 'hidden' && (
            <label>Access code
              <input maxLength={32} pattern="[A-Za-z0-9-]{4,32}" value={form.access_code} onChange={set('access_code')}
                placeholder={tier?.has_access_code ? 'Leave empty to keep the current code' : 'e.g. SPONSOR-2026'}
                required={!tier?.has_access_code} />
            </label>
          )}
        </div>
        {tier && (
          <label className="radio"><input type="checkbox" checked={form.on_sale} onChange={set('on_sale')} /> On sale (untick to stop sales for this ticket type)</label>
        )}
        <div className="row-left">
          <button type="submit" disabled={saving || !dirty}>{saving ? 'Saving…' : tier ? 'Save changes' : 'Add ticket type'}</button>
          {!tier && <button type="button" className="secondary" onClick={onCancelNew}>Cancel</button>}
          {tier && !tier.has_orders && <button type="button" className="link danger-link" onClick={remove}>Delete</button>}
          {tier && dirty && <span className="save-state unsaved">Unsaved changes</span>}
        </div>
      </fieldset>
    </form>
  );
}

export default function StepTickets({ event, onSaved }) {
  const [adding, setAdding] = useState(event.ticket_types.length === 0);
  const [dragFrom, setDragFrom] = useState(null);
  const [overIndex, setOverIndex] = useState(null);
  const [error, setError] = useState(null);
  const editable = !['cancelled', 'ended'].includes(event.status);
  const tiers = event.ticket_types;

  async function saveOrder(ids) {
    setError(null);
    try {
      onSaved(await api.post(`/organizer/events/${event.id}/ticket-types/reorder`, { ids }));
    } catch (err) {
      setError(err);
    }
  }

  function move(index, delta) {
    const ids = tiers.map((t) => t.id);
    const [id] = ids.splice(index, 1);
    ids.splice(index + delta, 0, id);
    saveOrder(ids);
  }

  function dragProps(index) {
    return {
      // Only the handle starts a drag, so selecting text in the inputs still works.
      handle: {
        draggable: true,
        onDragStart: (e) => { setDragFrom(index); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', String(index)); },
        onDragEnd: () => { setDragFrom(null); setOverIndex(null); },
      },
      drop: {
        onDragOver: (e) => { if (dragFrom !== null) { e.preventDefault(); setOverIndex(index); } },
        onDragLeave: () => setOverIndex(null),
        onDrop: (e) => {
          e.preventDefault();
          if (dragFrom === null || dragFrom === index) return;
          move(dragFrom, index - dragFrom);
          setDragFrom(null);
          setOverIndex(null);
        },
      },
    };
  }

  return (
    <section>
      <div className="card">
        <h2>Ticket types</h2>
        <p className="hint">Add every kind of ticket you sell. Drag them, or use the arrows, to set the order buyers see.</p>
        <ErrorMessage error={error} />
      </div>
      {tiers.map((t, i) => (
        <TierCard key={`${t.id}-${t.position}-${t.sold}`} event={event} tier={t} editable={editable} onSaved={onSaved}
          dragProps={dragProps(i)} onMove={move} index={i} count={tiers.length} dragOver={overIndex === i && dragFrom !== i} />
      ))}
      {adding && editable && (
        <TierCard event={event} editable onSaved={(e) => { onSaved(e); setAdding(false); }} onCancelNew={() => setAdding(false)} />
      )}
      {!adding && editable && (
        <button type="button" className="secondary add-tier" onClick={() => setAdding(true)}>+ Add another ticket type</button>
      )}
    </section>
  );
}
