export const rwf = (n) => (Number(n) === 0 ? 'Free' : `${Number(n).toLocaleString('en-US')} RWF`);

export const when = (iso) =>
  iso
    ? new Date(iso).toLocaleString('en-GB', {
        timeZone: 'Africa/Kigali',
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

// Dates are stored in UTC on the server and shown in Kigali time (UTC+2, no daylight saving).
const KIGALI_OFFSET_MS = 2 * 60 * 60 * 1000;

// UTC ISO string -> value for <input type="datetime-local"> in Kigali time.
export const toKigaliInput = (iso) =>
  iso ? new Date(new Date(iso).getTime() + KIGALI_OFFSET_MS).toISOString().slice(0, 16) : '';

// <input type="datetime-local"> value (Kigali time) -> ISO string with offset, or null.
export const fromKigaliInput = (value) => (value ? `${value}:00+02:00` : null);

export const CATEGORIES = ['concert', 'conference', 'sports', 'church', 'festival', 'theatre', 'other'];

export const STATUS_LABELS = {
  draft: 'Draft',
  published: 'On sale',
  paused: 'Sales paused',
  ended: 'Ended',
  cancelled: 'Cancelled',
  pending: 'Awaiting payment',
  paid: 'Paid',
  expired: 'Expired',
  failed: 'Failed',
  refund_pending: 'Refund in progress',
  refunded: 'Refunded',
};

export const capitalize = (s) => (s ? s[0].toUpperCase() + s.slice(1) : '');
