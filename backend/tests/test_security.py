"""Security tests from the plan (Phase 4: tests based on the abuse cases), automated
so they run again after every change (Phase 6: re-testing).

Run with:  python manage.py test
"""
import secrets
import threading
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from accounts import totp
from accounts.models import User
from audit.models import AuditEntry
from audit.services import verify_chain
from events.models import TicketType
from orders import services
from orders.models import MockProviderTransaction, Order, Ticket
from orders.payment_provider import get_provider

from .helpers import PASSWORD, Browser, checkout, new_buyer, new_event, new_organizer, unique_email


class SecurityTestCase(TestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters between tests
        self.org = new_organizer()
        self.event, self.tt = new_event(self.org.user, price=5000)


class PriceTamperingTests(SecurityTestCase):
    """Plan Phases 1-4: the client is not allowed to change the price."""

    def test_checkout_with_a_price_is_rejected_and_creates_no_order(self):
        buyer = new_buyer()
        r = checkout(buyer, self.tt, price=5)
        self.assertEqual(r.status_code, 400)
        self.assertIn("price", r.json()["unexpected_fields"])
        self.assertFalse(Order.objects.filter(buyer=buyer.user).exists())
        self.assertTrue(AuditEntry.objects.filter(action="checkout.rejected_tampering", actor=buyer.user).exists())

    def test_other_price_like_fields_are_rejected(self):
        buyer = new_buyer()
        for field in ("total", "amount", "unit_price", "unitPrice"):
            self.assertEqual(checkout(buyer, self.tt, **{field: 1}).status_code, 400, field)

    def test_price_comes_from_the_database(self):
        buyer = new_buyer()
        r = checkout(buyer, self.tt)
        self.assertEqual(r.status_code, 201)
        order = Order.objects.get(pk=r.json()["id"])
        self.assertEqual(order.unit_price, 5000)
        self.assertEqual(order.total, 10000)


class InputValidationTests(SecurityTestCase):
    def test_bad_quantities_are_rejected(self):
        buyer = new_buyer()
        for q in (0, 11, -1, 1.5, "abc"):
            self.assertEqual(checkout(buyer, self.tt, quantity=q).status_code, 400, q)

    def test_phone_must_be_mtn_or_airtel_rwanda(self):
        buyer = new_buyer()
        self.assertEqual(checkout(buyer, self.tt, phone="0711111111").status_code, 400)

    def test_same_checkout_twice_creates_one_order(self):
        buyer = new_buyer()
        key = str(uuid.uuid4())
        a = checkout(buyer, self.tt, idempotency_key=key)
        b = checkout(buyer, self.tt, idempotency_key=key)
        self.assertEqual(a.json()["id"], b.json()["id"])
        self.assertEqual(Order.objects.filter(buyer=buyer.user).count(), 1)


class AccessControlTests(SecurityTestCase):
    """Plan Phase 2: information disclosure and elevation of privilege."""

    def test_someone_elses_order_gives_404(self):
        alice, bob = new_buyer(), new_buyer()
        order_id = checkout(alice, self.tt).json()["id"]
        self.assertEqual(alice.get(f"/api/orders/{order_id}").status_code, 200)
        self.assertEqual(bob.get(f"/api/orders/{order_id}").status_code, 404)
        self.assertEqual(bob.post(f"/api/orders/{order_id}/refresh").status_code, 404)
        self.assertEqual(bob.post(f"/api/dev/orders/{order_id}/pay", {"decision": "approve"}).status_code, 404)
        self.assertEqual(Order.objects.get(pk=order_id).status, "pending")

    def test_buyer_cannot_use_organizer_api(self):
        buyer = new_buyer()
        self.assertEqual(buyer.get("/api/organizer/events").status_code, 403)
        r = buyer.post("/api/organizer/events", {"title": "x", "venue": "y", "description": "z",
                                                 "starts_at": "2030-01-01T10:00:00+02:00"})
        self.assertEqual(r.status_code, 403)

    def test_organizer_cannot_reach_another_organizers_event(self):
        other = new_organizer()
        for path in (f"/api/organizer/events/{self.event.id}", f"/api/organizer/events/{self.event.id}/attendees"):
            self.assertEqual(other.get(path).status_code, 404, path)
        self.assertEqual(other.post(f"/api/organizer/events/{self.event.id}/cancel").status_code, 404)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, "active")

    def test_cannot_register_as_admin(self):
        b = Browser()
        r = b.post("/api/auth/register", {"email": unique_email(), "password": PASSWORD, "role": "admin"})
        self.assertEqual(r.status_code, 400)

    def test_signed_out_user_cannot_checkout(self):
        self.assertEqual(checkout(Browser(), self.tt).status_code, 403)


class PaymentCallbackTests(SecurityTestCase):
    """Plan Phase 2: payment callbacks are only a hint."""

    def _order(self):
        buyer = new_buyer()
        return Order.objects.get(pk=checkout(buyer, self.tt).json()["id"])

    def test_fake_webhook_leaves_order_unpaid(self):
        order = self._order()
        r = Browser().client.post("/api/webhooks/payment",
                                  {"referenceId": str(order.payment_ref), "status": "SUCCESSFUL", "amount": 10000},
                                  format="json")
        self.assertEqual(r.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.tickets.count(), 0)

    def test_replayed_webhook_counts_once(self):
        order = self._order()
        get_provider().simulate_buyer_response(order.payment_ref, True)
        for _ in range(3):
            Browser().client.post("/api/webhooks/payment", {"referenceId": str(order.payment_ref)}, format="json")
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.tickets.count(), 2)

    def test_amount_mismatch_is_not_accepted(self):
        order = self._order()
        MockProviderTransaction.objects.filter(ref=order.payment_ref).update(amount=5, status="SUCCESSFUL")
        self.assertEqual(services.confirm_payment(order.payment_ref, "test"), "amount_mismatch")
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        self.assertTrue(AuditEntry.objects.filter(action="payment.amount_mismatch", target=f"order:{order.id}").exists())

    def test_malformed_reference_is_rejected(self):
        r = Browser().client.post("/api/webhooks/payment", {"referenceId": "1' OR '1'='1"}, format="json")
        self.assertEqual(r.status_code, 400)


class HoldExpiryTests(SecurityTestCase):
    """Plan Phase 2: denial of service by holding every ticket."""

    def test_expired_hold_releases_seats_and_late_payment_is_flagged(self):
        _, small = new_event(self.org.user, capacity=2)
        buyer = new_buyer()
        order = Order.objects.get(pk=checkout(buyer, small).json()["id"])
        small.refresh_from_db()
        self.assertEqual(small.sold, 2)

        Order.objects.filter(pk=order.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        services.expire_holds()
        order.refresh_from_db()
        small.refresh_from_db()
        self.assertEqual(order.status, "expired")
        self.assertEqual(small.sold, 0)

        get_provider().simulate_buyer_response(order.payment_ref, True)
        self.assertEqual(services.confirm_payment(order.payment_ref, "test"), "paid_after_expiry")
        self.assertEqual(order.tickets.count(), 0)
        self.assertTrue(AuditEntry.objects.filter(action="payment.after_expiry_refund_needed").exists())


class GateCheckInTests(SecurityTestCase):
    """Plan Phase 1: forged or shared tickets."""

    def _paid_ticket(self):
        buyer = new_buyer()
        order_id = checkout(buyer, self.tt).json()["id"]
        buyer.post(f"/api/dev/orders/{order_id}/pay", {"decision": "approve"})
        return Ticket.objects.filter(order_id=order_id).first()

    def test_ticket_is_accepted_once(self):
        ticket = self._paid_ticket()
        self.assertRegex(ticket.token, r"^[A-Za-z0-9_-]{43}$")  # 256-bit random token
        self.assertEqual(self.org.post("/api/organizer/checkin", {"token": ticket.token}).status_code, 200)
        second = self.org.post("/api/organizer/checkin", {"token": ticket.token})
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["result"], "already_used")

    def test_forged_token_and_other_organizers_ticket_are_rejected(self):
        forged = self.org.post("/api/organizer/checkin", {"token": secrets.token_urlsafe(32)})
        self.assertEqual(forged.json()["result"], "invalid")
        ticket = self._paid_ticket()
        other = new_organizer()
        self.assertEqual(other.post("/api/organizer/checkin", {"token": ticket.token}).json()["result"], "invalid")


class LoginTests(SecurityTestCase):
    """Plan Phase 2: spoofing."""

    def test_account_locks_after_five_failures(self):
        buyer = new_buyer()
        b = Browser()
        for _ in range(5):
            self.assertEqual(b.post("/api/auth/login", {"email": buyer.email, "password": "wrong password!"}).status_code, 401)
        self.assertEqual(b.post("/api/auth/login", {"email": buyer.email, "password": PASSWORD}).status_code, 429)

    def test_login_is_rate_limited_per_ip(self):
        b = Browser()
        codes = [b.post("/api/auth/login", {"email": unique_email(), "password": "whatever1234"}).status_code
                 for _ in range(11)]
        self.assertEqual(codes[:10], [401] * 10)
        self.assertEqual(codes[10], 429)

    def test_same_error_for_unknown_email_and_wrong_password(self):
        buyer = new_buyer()
        b = Browser()
        unknown = b.post("/api/auth/login", {"email": "nobody@example.com", "password": "whatever1234"})
        wrong = b.post("/api/auth/login", {"email": buyer.email, "password": "whatever1234"})
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.json(), wrong.json())

    def test_sql_injection_in_login(self):
        r = Browser().post("/api/auth/login", {"email": "' OR 1=1 --", "password": "' OR '1'='1"})
        self.assertEqual(r.status_code, 401)

    def test_weak_passwords_rejected(self):
        for pw in ("short", "password123", "1234567890123"):
            r = Browser().post("/api/auth/register", {"email": unique_email(), "password": pw, "role": "buyer"})
            self.assertEqual(r.status_code, 400, pw)

    def test_passwords_stored_with_argon2(self):
        buyer = new_buyer()
        self.assertTrue(buyer.user.password.startswith("argon2$"))
        self.assertNotIn(PASSWORD, buyer.user.password)

    def test_organizer_without_2fa_cannot_manage_events(self):
        b = Browser()
        b.post("/api/auth/register", {"email": unique_email("org"), "password": PASSWORD, "role": "organizer"})
        r = b.get("/api/organizer/events")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "mfa_setup_required")

    def test_organizer_login_needs_code_and_refuses_reused_code(self):
        org = new_organizer()
        b = Browser()
        self.assertEqual(b.post("/api/auth/login", {"email": org.email, "password": PASSWORD}).json(), {"mfa_required": True})
        self.assertEqual(b.get("/api/organizer/events").status_code, 403)  # not signed in yet

        last = User.objects.get(pk=org.user.pk).totp_last_counter
        reused = b.post("/api/auth/login/2fa", {"code": totp.code_for_counter(org.secret, last)})
        self.assertEqual(reused.status_code, 401)
        ok = b.post("/api/auth/login/2fa", {"code": totp.code_for_counter(org.secret, last + 1)})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(b.get("/api/organizer/events").status_code, 200)

    def test_session_id_changes_at_login(self):
        buyer = new_buyer()
        b = Browser()
        b.get("/api/auth/csrf")
        before = b.client.cookies.get(settings.SESSION_COOKIE_NAME)
        b.post("/api/auth/login", {"email": buyer.email, "password": PASSWORD})
        self.assertNotEqual(before and before.value, b.client.cookies[settings.SESSION_COOKIE_NAME].value)


class CsrfAndXssTests(SecurityTestCase):
    def test_post_without_csrf_token_is_rejected(self):
        buyer = new_buyer()
        r = buyer.post("/api/checkout", {"ticket_type_id": self.tt.id, "quantity": 1, "phone": "0788123456",
                                         "idempotency_key": str(uuid.uuid4())}, csrf=False)
        self.assertEqual(r.status_code, 403)

    def test_login_is_csrf_protected_too(self):
        buyer = new_buyer()
        r = Browser().post("/api/auth/login", {"email": buyer.email, "password": PASSWORD}, csrf=False)
        self.assertEqual(r.status_code, 403)

    def test_wrong_csrf_token_is_rejected(self):
        buyer = new_buyer()
        r = buyer.client.post("/api/auth/logout", {}, format="json", HTTP_X_CSRFTOKEN="forged" * 8)
        self.assertEqual(r.status_code, 403)

    def test_script_in_description_is_returned_as_plain_json_text(self):
        """The API returns JSON (never HTML), and the React app renders text with
        JSX, which escapes it. The CSP blocks inline scripts as a second layer."""
        event, _ = new_event(self.org.user, description='<script>alert("xss")</script>')
        r = Browser().get(f"/api/events/{event.id}")
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertEqual(r.json()["description"], '<script>alert("xss")</script>')


class HeaderTests(SecurityTestCase):
    """Plan Phase 5: security headers and cookies."""

    def test_security_headers(self):
        r = Browser().get("/api/events")
        csp = r["Content-Security-Policy"]
        for part in ("default-src 'self'", "script-src 'self'", "frame-ancestors 'none'", "object-src 'none'"):
            self.assertIn(part, csp)
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r["X-Frame-Options"], "DENY")
        self.assertEqual(r["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(r["Cross-Origin-Opener-Policy"], "same-origin")

    def test_session_cookie_flags(self):
        buyer = new_buyer()
        cookie = buyer.client.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    def test_errors_do_not_leak_details(self):
        r = Browser().get("/api/orders/999999")
        self.assertEqual(r.status_code, 403)  # not signed in
        buyer = new_buyer()
        r = buyer.get("/api/orders/999999")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not found."})


class AuditLogTests(SecurityTestCase):
    """Plan Phase 2: repudiation."""

    def test_audit_log_is_append_only_and_tamper_evident(self):
        self.org.post(f"/api/organizer/events/{self.event.id}/cancel")
        entry = AuditEntry.objects.get(action="event.cancelled", target=f"event:{self.event.id}")
        self.assertEqual(entry.actor_id, self.org.user.id)

        for sql in ("UPDATE audit_auditentry SET actor_id = NULL WHERE id = %s",
                    "DELETE FROM audit_auditentry WHERE id = %s"):
            with self.assertRaisesRegex(Exception, "append-only"):
                with transaction.atomic(), connection.cursor() as cur:
                    cur.execute(sql, [entry.id])
        self.assertEqual(verify_chain(), (True, None))

        # Someone with database admin rights drops the trigger and edits a row: detected.
        with connection.cursor() as cur:
            cur.execute("DROP TRIGGER audit_no_update ON audit_auditentry")
            cur.execute("UPDATE audit_auditentry SET actor_id = NULL WHERE id = %s", [entry.id])
        self.assertFalse(verify_chain()[0])


class OversellingTests(TransactionTestCase):
    """Plan Phase 3: two buyers must not get the last ticket. Uses real concurrent
    database connections (threads), not one after the other."""

    def test_two_simultaneous_buyers_for_the_last_ticket(self):
        org = User.objects.create_user(unique_email("org"), PASSWORD, role="organizer")
        _, tt = new_event(org, capacity=1)
        buyers = [User.objects.create_user(unique_email("buyer"), PASSWORD) for _ in range(2)]
        start = threading.Barrier(2)
        results = []

        def buy(user):
            try:
                start.wait()
                services.create_order(buyer=user, ticket_type_id=tt.id, quantity=1,
                                      phone="250788123456", idempotency_key=uuid.uuid4())
                results.append("ok")
            except services.CheckoutError:
                results.append("sold_out")
            finally:
                connection.close()

        threads = [threading.Thread(target=buy, args=(u,)) for u in buyers]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), ["ok", "sold_out"])
        tt.refresh_from_db()
        self.assertEqual(tt.sold, 1)

    def test_database_refuses_to_go_over_capacity(self):
        org = User.objects.create_user(unique_email("org"), PASSWORD, role="organizer")
        _, tt = new_event(org, capacity=3)
        with self.assertRaises(IntegrityError):
            TicketType.objects.filter(pk=tt.pk).update(sold=4)
