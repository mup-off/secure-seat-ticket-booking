import itertools
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import totp
from accounts.models import User
from events.models import Event, TicketType

PASSWORD = "correct horse battery"
_counter = itertools.count(1)


def unique_name(prefix="user"):
    return f"{prefix}{next(_counter)}-{uuid.uuid4().hex[:6]}"


def unique_email(prefix="user"):
    return f"{unique_name(prefix)}@example.com"


def register_body(prefix, role, password=PASSWORD):
    name = unique_name(prefix)
    return {"username": name, "email": f"{name}@example.com", "password": password, "role": role}


class Browser:
    """Behaves like the React app in a browser: keeps cookies and sends the CSRF
    token in the X-CSRFToken header. CSRF checks are ON, as in production."""

    def __init__(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/auth/csrf")

    @property
    def csrf_token(self):
        return self.client.cookies[settings.CSRF_COOKIE_NAME].value

    def get(self, path):
        return self.client.get(path)

    def post(self, path, data=None, csrf=True):
        headers = {"HTTP_X_CSRFTOKEN": self.csrf_token} if csrf else {}
        return self.client.post(path, data or {}, format="json", **headers)


def new_buyer():
    b = Browser()
    body = register_body("buyer", "buyer")
    b.username, b.email = body["username"], body["email"]
    r = b.post("/api/auth/register", body)
    assert r.status_code == 201, r.content
    b.user = User.objects.get(username=b.username)
    return b


def new_organizer():
    b = Browser()
    body = register_body("org", "organizer")
    b.username, b.email = body["username"], body["email"]
    r = b.post("/api/auth/register", body)
    assert r.status_code == 201, r.content
    b.secret = b.get("/api/auth/2fa/setup").json()["secret"]
    r = b.post("/api/auth/2fa/setup", {"code": totp.code_for_counter(b.secret, totp.current_counter())})
    assert r.status_code == 200, r.content
    b.user = User.objects.get(username=b.username)
    return b


def new_event(organizer_user, price=5000, capacity=100, description="A great night.", status="published", **tier):
    """A complete, published event with one ticket type (created directly in the database)."""
    start = timezone.now() + timedelta(days=30)
    event = Event.objects.create(
        organizer=organizer_user, title="Kigali Jazz Night", description=description, category="concert",
        venue="Kigali Arena", venue_address="KG 17 Ave, Kigali", contact_phone="250788000000",
        starts_at=start, ends_at=start + timedelta(hours=4), status=status, published_at=timezone.now())
    tt = TicketType.objects.create(event=event, name="Regular", price=price, capacity=capacity, position=1, **tier)
    return event, tt


def checkout(buyer, ticket_type, **overrides):
    body = {"ticket_type_id": ticket_type.id, "quantity": 2, "phone": "0788123456",
            "idempotency_key": str(uuid.uuid4())}
    body.update(overrides)
    return buyer.post("/api/checkout", body)
