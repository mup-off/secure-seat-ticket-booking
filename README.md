# SecureSeat

An event ticketing web app built by following the Secure SDLC plan in [plan.md](plan.md). Organizers create events and ticket types; buyers pay with mobile money (MTN MoMo / Airtel Money) and get ticket codes that are checked in once at the gate.

## Run it

Needs Node.js 22.13 or newer (it uses the built-in `node:sqlite`).

```bash
npm install
npm run dev        # http://localhost:3000
npm test           # security test suite
npm run audit      # dependency scan
```

Optionally copy `.env.example` to `.env` first. In development no real payment is made: the order page shows **Approve payment / Decline** buttons that play the part of the buyer's phone.

To try the whole flow:

1. Sign up as an organizer, add the setup key to an authenticator app, and enter the code.
2. Create an event and a ticket type.
3. In another browser (or a private window), sign up as a buyer and buy tickets.
4. Approve the payment and copy a ticket code.
5. As the organizer, open **Check-in** and enter the code. A second check-in of the same code is rejected.

## Layout

| Path | What it holds |
| --- | --- |
| `src/app.js` | Express setup: security headers, session cookie, CSRF, error handler |
| `src/security/` | CSRF, passwords, TOTP 2FA, access control, rate limits, input validation, session store |
| `src/services/orders.js` | Checkout, payment confirmation, hold expiry, check-in |
| `src/services/paymentProvider.js` | Payment provider adapter (mock only so far) |
| `src/services/audit.js` | Append-only, hash-chained audit log |
| `src/routes/` | Auth, shop, organizer, webhooks, dev-only payments |
| `test/security.test.js` | Tests for each abuse case in the plan |
| `.github/workflows/security.yml` | CI: tests, npm audit, Semgrep, gitleaks |

## Production

`NODE_ENV=production` refuses to start without a `SESSION_SECRET` of at least 32 characters, and refuses the mock payment provider. Run it behind HTTPS (set `TRUST_PROXY=1` behind a proxy). See `SecureSeat-Security-Implementation.docx` for what is done and what is still open.
