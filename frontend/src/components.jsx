// Shared bits. Every piece of text is rendered through JSX ({value}), which escapes
// it, so a description like "<script>…" shows up as text and never runs.

export function ErrorMessage({ error }) {
  if (!error) return null;
  return <p className="error" role="alert">{error.message || String(error)}</p>;
}

export function Status({ value }) {
  return <span className={`status ${value}`}>{value}</span>;
}
