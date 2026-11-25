// Shared bits. Every piece of text is rendered through JSX ({value}), which escapes
// it, so a description like "<script>…" shows up as text and never runs.
import { STATUS_LABELS } from './format.js';

export function ErrorMessage({ error }) {
  if (!error) return null;
  const problems = error.body?.problems;
  return (
    <div className="error" role="alert">
      {error.message || String(error)}
      {problems?.length > 0 && (
        <ul>{problems.map((p) => <li key={p}>{p}</li>)}</ul>
      )}
    </div>
  );
}

export function Status({ value }) {
  return <span className={`status ${value}`}>{STATUS_LABELS[value] || value}</span>;
}
