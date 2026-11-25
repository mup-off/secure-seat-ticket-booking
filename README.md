# SecureSeat

An event ticketing web app built by following the Secure SDLC plan in [plan.md](plan.md). Organizers create events and ticket types; buyers pay with mobile money (MTN MoMo / Airtel Money) and get ticket codes that are checked in once at the gate.

**Stack:** React (Vite) · Django 5.2 + Django REST framework · PostgreSQL

## Set up

Needs Python 3.12+, Node.js 20+ and PostgreSQL.

**1. Database.** Create a dedicated role; don't use the `postgres` superuser. `CREATEDB` is only needed so Django can create its test database.

```
psql -U postgres -c "CREATE ROLE secureseat LOGIN CREATEDB PASSWORD 'choose-a-password'" -c "CREATE DATABASE secureseat OWNER secureseat"
```

**2. Backend**

```
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
copy .env.example .env            # then set DB_PASSWORD
python manage.py migrate
python manage.py runserver        # http://127.0.0.1:8000
```

**3. Frontend** (in another terminal)

```
cd frontend
npm install
npm run dev                       # http://localhost:5173 (forwards /api to Django)
```

In development no real payment is made: the order page shows **Approve payment / Decline** buttons that play the part of the buyer's phone.

## Checks

| Command (folder) | What it does |
| --- | --- |
| `python manage.py test` (backend) | Security test suite |
| `bandit -r . -x ./.venv,./tests` (backend) | Static analysis |
| `pip-audit -r requirements.txt` (backend) | Python dependency scan |
| `npm run check:xss` (frontend) | Fails if code renders raw HTML |
| `npm audit` (frontend) | JavaScript dependency scan |
| `python manage.py verify_audit_log` (backend) | Checks the audit log's hash chain |
| `python manage.py housekeeping` (backend) | Releases expired holds, marks finished events as ended, retries refunds; schedule every minute |

CI runs all of these plus Semgrep and gitleaks: `.github/workflows/security.yml`.

## Production

`DJANGO_ENV=production` refuses to start without a strong `SECRET_KEY` and refuses the mock payment provider. Build the frontend (`npm run build`); Django then serves it from `frontend/dist`, so the pages and the API share one origin and the same security headers. Run behind HTTPS. See `SecureSeat-Security-Implementation.docx` for what is done and what is still open.
