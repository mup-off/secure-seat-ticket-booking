"""Login with a username instead of an email address."""
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User

from .helpers import PASSWORD, Browser, new_buyer, register_body


class UsernameTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_login_with_username(self):
        buyer = new_buyer()
        r = Browser().post("/api/auth/login", {"username": buyer.username, "password": PASSWORD})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["username"], buyer.username)

    def test_username_is_case_insensitive(self):
        buyer = new_buyer()
        r = Browser().post("/api/auth/login", {"username": buyer.username.upper(), "password": PASSWORD})
        self.assertEqual(r.status_code, 200)

    def test_email_no_longer_logs_in(self):
        buyer = new_buyer()
        r = Browser().post("/api/auth/login", {"email": buyer.email, "password": PASSWORD})
        self.assertEqual(r.status_code, 400)  # "email" is not an accepted field
        r = Browser().post("/api/auth/login", {"username": buyer.email, "password": PASSWORD})
        self.assertEqual(r.status_code, 401)

    def test_lookalike_username_is_taken(self):
        body = register_body("jean", "buyer")
        Browser().post("/api/auth/register", {**body, "username": "Jean.Paul"})
        r = Browser().post("/api/auth/register", {**register_body("x", "buyer"), "username": "jean.paul"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("taken", str(r.json()["username"]))

    def test_invalid_and_reserved_usernames(self):
        for name in ("ab", "has space", "<script>", "-dash-first", "a" * 31, "admin", "Support", "secureseat"):
            r = Browser().post("/api/auth/register", {**register_body("x", "buyer"), "username": name})
            self.assertEqual(r.status_code, 400, name)

    def test_password_cannot_match_username(self):
        body = register_body("x", "buyer")
        body.update(username="kigalijazz2026", password="kigalijazz2026")
        self.assertEqual(Browser().post("/api/auth/register", body).status_code, 400)

    def test_database_refuses_uppercase_username(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=new_buyer().user.pk).update(username="UPPER")

    def test_availability_check(self):
        buyer = new_buyer()
        b = Browser()
        self.assertEqual(b.get(f"/api/auth/username-available?username={buyer.username}").json()["available"], False)
        self.assertEqual(b.get("/api/auth/username-available?username=fresh-name-123").json(), {"available": True})
        self.assertFalse(b.get("/api/auth/username-available?username=admin").json()["available"])

    def test_availability_check_is_rate_limited(self):
        b = Browser()
        codes = [b.get(f"/api/auth/username-available?username=probe{i}").status_code for i in range(31)]
        self.assertEqual(codes[-1], 429)
