# Secure SDLC for an Event Ticketing Web App


## Introduction

This document applies security to every phase of the Software Development Life Cycle (SDLC) for a web application that sells event tickets. Organizers create events and ticket types, buyers pay (mostly with MTN MoMo or Airtel Money) and receive their ticket by email or SMS, and staff scan tickets at the gate.

The approach is "shift left": security is planned from the requirements phase instead of being tested only at the end. Each phase below lists the security activity, how it applies to the ticketing app, and the deliverable it produces.

## Phase 1: Requirements

**Activity:** Write security requirements alongside the feature requirements, and write abuse cases (what an attacker would try) next to the normal use cases.

**Security requirements for the ticketing app:**

- Users must sign in to buy tickets, and organizers must verify their phone or email.
- Only the event's owner can edit that event or see its attendee list.
- The client is not allowed to set or change the price. A checkout request sends only the ticket type and quantity, and only the organizer can set prices.
- The app never asks for or handles the buyer's mobile money PIN or card details. The payment provider handles them.
- An order is marked as paid only after the payment provider confirms the payment.
- Each ticket's QR code contains a random, unguessable token (or is signed by the server), so it cannot be forged.
- A ticket can be checked in only once at the gate.
- Personal data is protected under Rwanda's data protection law (Law No. 058/2021): register with NCSA as a data controller, follow the rules for storing personal data outside Rwanda (relevant if the app is hosted abroad), and define how long attendee data is kept.

**Abuse cases:**

- Change the price in the request before paying.
- Buy all the tickets with a bot to resell them.
- Open someone else's order by changing the ID in the URL.
- Forge a ticket QR code, or share a screenshot of one ticket with several people.
- Replay or duplicate a payment callback so one payment counts twice.
- Abuse refunds (get a refund and still use the ticket).
- A fake organizer creates a scam event and collects payments.
- Guess the ticket links sent by email or SMS to download other people's tickets.

**Deliverable:** a list of security requirements. The OWASP ASVS (Application Security Verification Standard) is a good checklist to pick them from.

## Phase 2: Design

**Activity:** Threat modeling. Draw the system (browser, web server, database, payment provider, SMS/email provider and the gate scanner), mark the trust boundaries between them, then go through the threats one by one using STRIDE.

| Threat | Example in this app | How the design handles it |
| --- | --- | --- |
| Spoofing | Attacker logs in as an organizer | Strong passwords, rate-limited login, 2FA required for organizers (optional for buyers) |
| Tampering | Price changed from 5,000 to 5 RWF in the request | The client is not allowed to send a price: the server reads it from the database and rejects any checkout request that includes a price |
| Repudiation | Organizer says "I never cancelled that event" | Append-only (tamper-evident) audit log of important actions, stored separately from the main database |
| Information disclosure | `/orders/124` shows another person's order | Check that the order belongs to the user on every request |
| Denial of service | Bots hold every ticket at checkout | Holds expire after 10 minutes, rate limiting, CAPTCHA |
| Elevation of privilege | Buyer calls the admin API | Role-based access control enforced on the server |

**Other design decisions:**

- Payment callbacks are treated only as a hint. Some providers (for example MTN MoMo's collection API) do not sign their callbacks, so check each provider's documentation. Before marking an order paid, the server:
  - confirms the payment by calling the provider's status API,
  - checks that the amount and currency match the order,
  - processes each payment reference only once (idempotency), so replays have no effect.
- Least privilege: organizers can only manage their own events.

**Deliverable:** a data flow diagram with trust boundaries, plus the STRIDE table.

## Phase 3: Implementation

**Activity:** Follow secure coding practices. The OWASP Top 10 lists the most common web vulnerabilities to avoid.

- **SQL injection:** use parameterized queries or an ORM, never string concatenation.
- **Cross-site scripting (XSS):** escape user content such as event descriptions (including inside email and SMS templates), and set a Content Security Policy.
- **Passwords:** hash them with bcrypt or Argon2.
- **Sessions:** use Secure, HttpOnly, SameSite cookies, and protect forms against CSRF.
- **Input validation:** check every input on the server (quantity > 0, quantity ≤ max per order).
- **Price:** the checkout endpoint accepts only the ticket type and quantity. It rejects any request containing a price field with 400 Bad Request and logs the attempt. The amount charged is always computed on the server from the database.
- **File uploads:** check the type and size of uploaded event posters, and store them outside the web root.
- **Secrets:** keep payment API keys in environment variables or a secrets manager, never in the code or in Git.
- **Ticket tokens:** generate them with a cryptographically secure random generator, not sequential IDs.
- **Overselling:** a transaction alone does not stop two buyers getting the last ticket. Lock the row (`SELECT … FOR UPDATE`) or use an update that only succeeds if a ticket is left (`UPDATE … SET sold = sold + 1 WHERE sold < capacity`).
- **Double charges:** use idempotency keys on checkout and payment requests, so the same request cannot charge twice.

**Deliverable:** code snippets showing an insecure version next to the fixed version, plus peer code review notes.

## Phase 4: Testing

**Activity:** Check that the security requirements actually work.

- **SAST (static analysis):** scan the source code with Semgrep or SonarQube.
- **Dependency scanning:** run `npm audit` or Snyk to find vulnerable libraries.
- **Secret scanning:** run gitleaks to catch keys committed to Git.
- **In CI:** run SAST, dependency scanning and secret scanning on every pull request, not just once.
- **DAST (dynamic testing):** run OWASP ZAP against the running app.
- **Manual tests based on the abuse cases:**

| Test | Expected result |
| --- | --- |
| Change the price in Burp Suite or browser dev tools | Request is rejected (400 Bad Request), the attempt is logged, and no order is created |
| Change the order ID in the URL | 404 Not Found (so an attacker can't tell which orders exist) |
| Send a fake payment webhook | Order stays unpaid |
| Replay a real payment webhook | Payment is counted only once |
| Two buyers buy the last ticket at the same time | Only one purchase succeeds |
| Scan the same ticket twice at the gate | Second scan is rejected |
| Many failed logins on one account | Login is rate-limited |
| Submit a form from another site (CSRF) | Request is rejected |

**Deliverable:** a test report listing each test, its result and any fixes.

## Phase 5: Deployment

**Activity:** Secure the environment the app runs in.

- [ ] HTTPS only (TLS), with HSTS enabled
- [ ] Security headers set: CSP (including `frame-ancestors`, which replaces X-Frame-Options; keeping both is fine), X-Content-Type-Options, Referrer-Policy
- [ ] Rate limiting or a WAF in front of the app
- [ ] Database not exposed to the internet, and its user has limited permissions
- [ ] Debug mode off, and error messages don't show stack traces
- [ ] Separate dev, test and production environments, with different keys for each
- [ ] CI/CD pipeline and cloud account locked down with least-privilege access
- [ ] Automated, encrypted backups configured, and a restore tested

**Deliverable:** this deployment hardening checklist, completed.

## Phase 6: Maintenance

**Activity:** Keep the app secure after launch.

- **Logging and monitoring:** alert on failed logins and spikes in failed payments. Never log passwords, tokens or payment credentials, and mask phone numbers.
- **Patching:** update dependencies regularly.
- **Incident response plan:** for example, if payment keys leak, rotate them, review transactions and notify affected users. For a personal data breach, notify NCSA within the deadline set by Law No. 058/2021 (believed to be 48 hours; confirm it in the law's text).
- **Data retention:** delete or anonymize attendee data once the retention period ends.
- **Re-testing:** run the security tests again after each major change.

**Deliverable:** a monitoring plan and an incident response plan.

## Conclusion: one feature through all six phases

Following the "buy a ticket" feature through every phase shows how each phase builds on the one before.

| Phase | Buy a ticket: price tampering |
| --- | --- |
| Requirements | The client is not allowed to change the price; the buyer always pays the price set by the organizer |
| Design | STRIDE identifies tampering; the server reads the price from the database |
| Implementation | Checkout code rejects any request that includes a price |
| Testing | Adding or changing the price in Burp Suite gets the request rejected |
| Deployment | HTTPS stops a third party changing the request in transit; the buyer's own tampering is handled by the server-side price check |
| Maintenance | Alerts flag orders where the amount paid doesn't match the ticket price |
