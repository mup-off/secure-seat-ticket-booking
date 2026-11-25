// Small API client. Uses Django's session cookie (HttpOnly, so this code can't read
// it) and sends the CSRF token in the X-CSRFToken header on every request that
// changes something. No tokens are kept in localStorage.

function readCookie(name) {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : '';
}

const csrfToken = () => readCookie('__Host-csrftoken') || readCookie('csrftoken');

export class ApiError extends Error {
  constructor(status, body) {
    super(messageFrom(body) || `Request failed (${status})`);
    this.status = status;
    this.body = body;
  }
}

function messageFrom(body) {
  if (!body || typeof body !== 'object') return '';
  if (typeof body.detail === 'string') return body.detail;
  if (body.unexpected_fields) return 'This request contains fields that are not allowed. Reload the page and try again.';
  const first = Object.entries(body)[0];
  if (!first) return '';
  const [field, value] = first;
  const text = Array.isArray(value) ? value[0] : value;
  return field === 'non_field_errors' ? String(text) : `${field.replace(/_/g, ' ')}: ${text}`;
}

async function request(method, path, body) {
  const headers = { Accept: 'application/json' };
  const isForm = body instanceof FormData;
  if (method !== 'GET') {
    if (!isForm) headers['Content-Type'] = 'application/json'; // the browser sets the multipart boundary
    headers['X-CSRFToken'] = csrfToken();
  }
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, { detail: 'Cannot reach the server. Check that the backend and "npm run dev" are both running.' });
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body = {}) => request('POST', path, body),
  patch: (path, body = {}) => request('PATCH', path, body),
  del: (path) => request('DELETE', path),
  upload: (path, file, field = 'image') => {
    const form = new FormData();
    form.append(field, file);
    return request('POST', path, form);
  },
};
