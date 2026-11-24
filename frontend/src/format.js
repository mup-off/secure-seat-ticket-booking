export const rwf = (n) => `${Number(n).toLocaleString('en-US')} RWF`;

export const when = (iso) =>
  new Date(iso).toLocaleString('en-GB', {
    timeZone: 'Africa/Kigali',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
