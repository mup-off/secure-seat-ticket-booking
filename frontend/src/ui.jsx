// Interactive building blocks used across pages.
import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';

// ---------- Icons (inline SVG, no external requests) ----------
const paths = {
  calendar: 'M7 2v3M17 2v3M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z',
  pin: 'M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z',
  phone: 'M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  ticket: 'M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4V8zM13 6v2M13 11v2M13 16v2',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
};

export function Icon({ name, ...rest }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      <path d={paths[name]} />
    </svg>
  );
}

export function BrandMark() {
  // A ticket stub with an Imigongo zigzag cut.
  return (
    <svg className="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
      <rect x="3" y="8" width="34" height="24" rx="5" fill="#ffb627" />
      <circle cx="3" cy="20" r="4" fill="#0e0d12" />
      <circle cx="37" cy="20" r="4" fill="#0e0d12" />
      <path d="M10 26l4-6 4 6 4-6 4 6 4-6" stroke="#0e0d12" strokeWidth="2.6" fill="none" strokeLinejoin="round" />
      <path d="M10 14h20" stroke="#e2553b" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

// ---------- Loading placeholders ----------
export function Skeleton({ height = 120, count = 1 }) {
  return Array.from({ length: count }, (_, i) => <div key={i} className="skeleton" style={{ height, marginBottom: 16 }} />);
}

// ---------- Time ----------
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function Countdown({ to, label = 'Starts in' }) {
  const now = useNow();
  const ms = new Date(to).getTime() - now;
  if (!to || ms <= 0) return null;
  const parts = [
    ['days', Math.floor(ms / 86400000)],
    ['hrs', Math.floor(ms / 3600000) % 24],
    ['min', Math.floor(ms / 60000) % 60],
    ['sec', Math.floor(ms / 1000) % 60],
  ];
  return (
    <div>
      <span className="eyebrow">{label}</span>
      <div className="countdown" role="timer" aria-live="off">
        {parts.map(([unit, value]) => (
          <div key={unit}><b>{String(value).padStart(2, '0')}</b><small>{unit}</small></div>
        ))}
      </div>
    </div>
  );
}

export function relativeDay(iso) {
  const days = Math.round((new Date(iso).setHours(0, 0, 0, 0) - new Date().setHours(0, 0, 0, 0)) / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  if (days > 1 && days < 7) return `In ${days} days`;
  if (days >= 7 && days < 30) { const w = Math.round(days / 7); return `In ${w} week${w > 1 ? 's' : ''}`; }
  return null;
}

// ---------- Numbers that count up when they appear ----------
export function CountUp({ value, duration = 900, format = (n) => n.toLocaleString('en-US') }) {
  const [shown, setShown] = useState(0);
  const start = useRef(null);
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setShown(value); return undefined; }
    let frame;
    start.current = null;
    const step = (t) => {
      if (start.current === null) start.current = t;
      const p = Math.min((t - start.current) / duration, 1);
      setShown(Math.round(value * (1 - Math.pow(1 - p, 3))));
      if (p < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    // Browsers pause animation frames in background tabs: make sure the real number shows anyway.
    const done = setTimeout(() => setShown(value), duration + 100);
    return () => { cancelAnimationFrame(frame); clearTimeout(done); };
  }, [value, duration]);
  return format(shown);
}

// ---------- Progress bar ----------
export function Bar({ value, max, low = 0.15 }) {
  const ratio = max > 0 ? Math.min(value / max, 1) : 0;
  const left = max - value;
  return (
    <div className={`bar ${max > 0 && left / max <= low ? 'low' : ''}`} role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
      <span style={{ width: `${ratio * 100}%` }} />
    </div>
  );
}

// ---------- QR code (generated in the browser; rendered as an image, never as HTML) ----------
export function QrImage({ value, size = 180, alt = 'QR code' }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let alive = true;
    QRCode.toString(value, { type: 'svg', margin: 1, errorCorrectionLevel: 'M', color: { dark: '#0e0d12', light: '#f4ecdc' } })
      .then((svg) => alive && setSrc(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`))
      .catch(() => alive && setSrc(null));
    return () => { alive = false; };
  }, [value]);
  return src ? <img src={src} width={size} height={size} alt={alt} /> : <div className="skeleton" style={{ width: size, height: size }} />;
}

// ---------- Confetti burst ----------
const COLORS = ['#ffb627', '#e2553b', '#3fc1a5', '#f4ecdc', '#7cc4ff'];
export function Confetti({ pieces = 70 }) {
  const [items] = useState(() =>
    Array.from({ length: pieces }, (_, i) => ({
      left: Math.random() * 100,
      delay: Math.random() * 0.6,
      color: COLORS[i % COLORS.length],
      rotate: Math.random() * 360,
    })));
  const [done, setDone] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDone(true), 3400);
    return () => clearTimeout(t);
  }, []);
  if (done) return null;
  return (
    <div className="confetti" aria-hidden="true">
      {items.map((p, i) => (
        <i key={i} style={{ left: `${p.left}%`, background: p.color, animationDelay: `${p.delay}s`, transform: `rotate(${p.rotate}deg)` }} />
      ))}
    </div>
  );
}

// ---------- Copy to clipboard ----------
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

// ---------- Password strength (a hint only; the server makes the real decision) ----------
export function passwordScore(pw, username = '') {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 10) score++;
  if (pw.length >= 14) score++;
  if (/[a-z]/.test(pw) && /[A-Z0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw) || /\s/.test(pw)) score++;
  if (pw.length < 10) score = Math.min(score, 1);
  if (username && pw.toLowerCase().includes(username.toLowerCase())) score = 1;
  return Math.max(score, 1);
}
export const SCORE_LABELS = ['', 'Too weak', 'Okay', 'Good', 'Strong'];
