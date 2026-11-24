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


def unique_email(prefix="user"):
    return f"{prefix}{next(_counter)}-{uuid.uuid4().hex[:6]}@example.com"


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
    b.email = unique_email("buyer")
    r = b.post("/api/auth/register", {"email": b.email, "password": PASSWORD, "role": "buyer"})
    assert r.status_code == 201, r.content
    b.user = User.objects.get(email=b.email)
    return b


def new_organizer():
    b = Browser()
    b.email = unique_email("org")
    r = b.post("/api/auth/register", {"email": b.email, "password": PASSWORD, "role": "organizer"})
    assert r.status_code == 201, r.content
    b.secret = b.get("/api/auth/2fa/setup").json()["secret"]
    r = b.post("/api/auth/2fa/setup", {"code": totp.code_for_counter(b.secret, totp.current_counter())})
    assert r.status_code == 200, r.content
    b.user = User.objects.get(email=b.email)
    return b


def new_event(organizer_user, price=5000, capacity=100, description="A great night."):
    event = Event.objects.create(organizer=organizer_user, title="Kigali Jazz Night", venue="Kigali Arena",
                                 description=description, starts_at=timezone.now() + timedelta(days=30))
    tt = TicketType.objects.create(event=event, name="Regular", price=price, capacity=capacity)
    return event, tt


def checkout(buyer, ticket_type, **overrides):
    body = {"ticket_type_id": ticket_type.id, "quantity": 2, "phone": "0788123456",
            "idempotency_key": str(uuid.uuid4())}
    body.update(overrides)
    return buyer.post("/api/checkout", body)
