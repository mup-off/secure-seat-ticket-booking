// Split layout for login and sign-up: a poster panel and the form.
import { useState } from 'react';

export default function AuthLayout({ title, tagline, children }) {
  return (
    <div className="auth">
      <div className="art">
        <span className="eyebrow">SecureSeat</span>
        <h2>{title}</h2>
        <p>{tagline}</p>
      </div>
      <div className="panel">{children}</div>
    </div>
  );
}

export function PasswordInput({ label, value, onChange, autoComplete, minLength, children }) {
  const [visible, setVisible] = useState(false);
  return (
    <label>{label}
      <span className="input-wrap">
        <input type={visible ? 'text' : 'password'} required value={value} onChange={onChange} autoComplete={autoComplete} minLength={minLength} maxLength={128} />
        <button type="button" className="peek" onClick={() => setVisible(!visible)} aria-pressed={visible} aria-label={visible ? 'Hide password' : 'Show password'}>
          {visible ? 'Hide' : 'Show'}
        </button>
      </span>
      {children}
    </label>
  );
}
