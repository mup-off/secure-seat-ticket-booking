"""Tests for the event set-up flow (draft -> ticket types -> review -> publish) and
the server-side rules for events and ticket tiers."""
import io
import uuid
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from audit.models import AuditEntry
from events.models import Event, TicketType
from orders.models import Order, Ticket
from orders.services import expire_holds

from .helpers import Browser, checkout, new_buyer, new_event, new_organizer

KIGALI_START = (timezone.now() + timedelta(days=40)).strftime("%Y-%m-%dT19:00:00+02:00")
KIGALI_END = (timezone.now() + timedelta(days=40)).strftime("%Y-%m-%dT23:00:00+02:00")

COMPLETE_DETAILS = {
    "title": "Kigali Jazz Night", "description": "Live music all night.", "category": "concert",
    "venue": "Kigali Arena", "venue_address": "KG 17 Ave, Kigali", "contact_phone": "0788123456",
    "starts_at": KIGALI_START, "ends_at": KIGALI_END,
}
TIER = {"name": "Regular", "price": 5000, "capacity": 100}


def png_bytes(size=(64, 48)):
    out = io.BytesIO()
    Image.new("RGBA", size, (200, 30, 30, 255)).save(out, format="PNG")
    return out.getvalue()


class EventTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.org = new_organizer()

    def draft(self, **details):
        r = self.org.post("/api/organizer/events", details)
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def patch(self, path, data):
        return self.org.client.patch(path, data, format="json", HTTP_X_CSRFTOKEN=self.org.csrf_token)

    def delete(self, path):
        return self.org.client.delete(path, HTTP_X_CSRFTOKEN=self.org.csrf_token)

    def ready_draft(self):
        eid = self.draft(**COMPLETE_DETAILS)
        self.org.post(f"/api/organizer/events/{eid}/ticket-types", TIER)
        return eid


class DraftFlowTests(EventTestCase):
    def test_empty_draft_can_be_saved_and_resumed(self):
        eid = self.draft()
        self.assertEqual(Event.objects.get(pk=eid).status, "draft")
        r = self.patch(f"/api/organizer/events/{eid}", {"title": "Half-finished"})
        self.assertEqual(r.status_code, 200)
        again = self.org.get(f"/api/organizer/events/{eid}").json()
        self.assertEqual(again["title"], "Half-finished")
        self.assertIn("Add at least one ticket type.", again["publish_problems"])

    def test_draft_is_not_public_and_cannot_be_bought(self):
        eid = self.ready_draft()
        self.assertEqual(Browser().get(f"/api/events/{eid}").status_code, 404)
        self.assertNotIn(eid, [e["id"] for e in Browser().get("/api/events").json()])
        tt = TicketType.objects.get(event_id=eid)
        self.assertEqual(checkout(new_buyer(), tt).status_code, 404)

    def test_times_are_stored_in_utc(self):
        eid = self.draft(**COMPLETE_DETAILS)
        event = Event.objects.get(pk=eid)
        self.assertEqual(event.starts_at.utcoffset(), timedelta(0))
        self.assertEqual(event.starts_at.hour, 17)  # 19:00 Kigali = 17:00 UTC

    def test_preview_matches_public_page(self):
        eid = self.ready_draft()
        preview = self.org.get(f"/api/organizer/events/{eid}/preview").json()["page"]
        self.org.post(f"/api/organizer/events/{eid}/publish")
        public = Browser().get(f"/api/events/{eid}").json()
        preview.pop("status"), public.pop("status")
        self.assertEqual(preview, public)

    def test_only_drafts_can_be_deleted(self):
        eid = self.draft()
        self.assertEqual(self.delete(f"/api/organizer/events/{eid}").status_code, 204)
        live, _ = new_event(self.org.user)
        self.assertEqual(self.delete(f"/api/organizer/events/{live.id}").status_code, 409)


class PublishRuleTests(EventTestCase):
    def test_cannot_publish_without_a_ticket_type(self):
        eid = self.draft(**COMPLETE_DETAILS)
        r = self.org.post(f"/api/organizer/events/{eid}/publish")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Add at least one ticket type.", r.json()["problems"])
        self.assertEqual(Event.objects.get(pk=eid).status, "draft")

    def test_cannot_publish_incomplete_details(self):
        eid = self.draft(title="Only a title")
        self.org.post(f"/api/organizer/events/{eid}/ticket-types", TIER)
        r = self.org.post(f"/api/organizer/events/{eid}/publish")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Add the venue name and address, or an online link.", r.json()["problems"])

    def test_publish_when_complete(self):
        eid = self.ready_draft()
        r = self.org.post(f"/api/organizer/events/{eid}/publish")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Event.objects.get(pk=eid).status, "published")
        self.assertTrue(AuditEntry.objects.filter(action="event.published", target=f"event:{eid}").exists())

    def test_online_event_needs_https_link(self):
        eid = self.draft()
        self.assertEqual(self.patch(f"/api/organizer/events/{eid}", {"online_url": "http://example.com"}).status_code, 400)
        self.assertEqual(self.patch(f"/api/organizer/events/{eid}", {"online_url": "javascript:alert(1)"}).status_code, 400)
        self.assertEqual(self.patch(f"/api/organizer/events/{eid}", {"online_url": "https://meet.example.com/x"}).status_code, 200)

    def test_end_must_be_after_start(self):
        eid = self.draft()
        r = self.patch(f"/api/organizer/events/{eid}", {"starts_at": KIGALI_END, "ends_at": KIGALI_START})
        self.assertEqual(r.status_code, 400)

    def test_status_and_organizer_cannot_be_set_through_details(self):
        eid = self.draft()
        for field, value in (("status", "published"), ("organizer", 1), ("sold", 0)):
            self.assertEqual(self.patch(f"/api/organizer/events/{eid}", {field: value}).status_code, 400, field)
        self.assertEqual(Event.objects.get(pk=eid).status, "draft")


class TierRuleTests(EventTestCase):
    def test_negative_price_or_quantity_rejected(self):
        eid = self.draft(**COMPLETE_DETAILS)
        for bad in ({"price": -1}, {"capacity": -5}, {"capacity": 0}):
            r = self.org.post(f"/api/organizer/events/{eid}/ticket-types", {**TIER, **bad})
            self.assertEqual(r.status_code, 400, bad)

    def test_free_tickets_allowed(self):
        eid = self.draft(**COMPLETE_DETAILS)
        r = self.org.post(f"/api/organizer/events/{eid}/ticket-types", {**TIER, "price": 0})
        self.assertEqual(r.status_code, 201)

    def test_sales_must_end_before_event_ends(self):
        eid = self.draft(**COMPLETE_DETAILS)
        late = (timezone.now() + timedelta(days=41)).isoformat()
        r = self.org.post(f"/api/organizer/events/{eid}/ticket-types", {**TIER, "sales_end": late})
        self.assertEqual(r.status_code, 400)
        # Moving the event end earlier than a tier's sales end is also refused.
        ok_end = (timezone.now() + timedelta(days=39)).isoformat()
        self.org.post(f"/api/organizer/events/{eid}/ticket-types", {**TIER, "sales_end": ok_end})
        early = (timezone.now() + timedelta(days=38)).isoformat()
        r = self.patch(f"/api/organizer/events/{eid}", {"ends_at": early, "starts_at": (timezone.now() + timedelta(days=37)).isoformat()})
        self.assertEqual(r.status_code, 400)

    def test_tier_with_sales_cannot_be_deleted_or_shrunk_below_sold(self):
        event, tt = new_event(self.org.user, capacity=10)
        checkout(new_buyer(), tt, quantity=3)
        tt.refresh_from_db()
        self.assertEqual(tt.sold, 3)
        path = f"/api/organizer/events/{event.id}/ticket-types/{tt.id}"
        self.assertEqual(self.delete(path).status_code, 409)
        self.assertEqual(self.patch(path, {"capacity": 2}).status_code, 400)
        self.assertEqual(self.patch(path, {"capacity": 3}).status_code, 200)   # equal to sold is fine
        self.assertEqual(self.patch(path, {"capacity": 50}).status_code, 200)  # raising is fine
        self.assertEqual(self.patch(path, {"on_sale": False}).status_code, 200)  # stopping sales is fine
        self.assertTrue(TicketType.objects.filter(pk=tt.pk).exists())

    def test_unsold_tier_can_be_deleted(self):
        event, tt = new_event(self.org.user)
        extra = TicketType.objects.create(event=event, name="VIP", price=20000, capacity=10, position=2)
        self.assertEqual(self.delete(f"/api/organizer/events/{event.id}/ticket-types/{extra.id}").status_code, 200)
        self.assertFalse(TicketType.objects.filter(pk=extra.pk).exists())

    def test_price_change_applies_only_to_new_orders(self):
        event, tt = new_event(self.org.user, price=5000)
        first = Order.objects.get(pk=checkout(new_buyer(), tt, quantity=1).json()["id"])
        r = self.patch(f"/api/organizer/events/{event.id}/ticket-types/{tt.id}", {"price": 7000})
        self.assertEqual(r.status_code, 200)
        second = Order.objects.get(pk=checkout(new_buyer(), tt, quantity=1).json()["id"])
        first.refresh_from_db()
        self.assertEqual((first.unit_price, first.total), (5000, 5000))
        self.assertEqual((second.unit_price, second.total), (7000, 7000))
        change = AuditEntry.objects.filter(action="ticket_type.updated", target=f"ticket_type:{tt.id}").last()
        self.assertEqual(change.details["price"], [5000, 7000])

    def test_reorder(self):
        event, a = new_event(self.org.user)
        b = TicketType.objects.create(event=event, name="VIP", price=20000, capacity=10, position=2)
        r = self.org.post(f"/api/organizer/events/{event.id}/ticket-types/reorder", {"ids": [b.id, a.id]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([t["name"] for t in Browser().get(f"/api/events/{event.id}").json()["ticket_types"]],
                         ["VIP", "Regular"])

    def test_reorder_rejects_ids_from_another_event(self):
        event, a = new_event(self.org.user)
        _, foreign = new_event(new_organizer().user)
        r = self.org.post(f"/api/organizer/events/{event.id}/ticket-types/reorder", {"ids": [a.id, foreign.id]})
        self.assertEqual(r.status_code, 400)

    def test_other_organizer_cannot_touch_tiers(self):
        event, tt = new_event(self.org.user)
        other = new_organizer()
        path = f"/api/organizer/events/{event.id}/ticket-types/{tt.id}"
        r = other.client.patch(path, {"price": 1}, format="json", HTTP_X_CSRFTOKEN=other.csrf_token)
        self.assertEqual(r.status_code, 404)
        r = other.client.delete(path, HTTP_X_CSRFTOKEN=other.csrf_token)
        self.assertEqual(r.status_code, 404)
        tt.refresh_from_db()
        self.assertEqual(tt.price, 5000)


class SalesRuleTests(EventTestCase):
    def test_max_per_order_per_tier(self):
        _, tt = new_event(self.org.user, max_per_order=2)
        self.assertEqual(checkout(new_buyer(), tt, quantity=3).status_code, 400)
        self.assertEqual(checkout(new_buyer(), tt, quantity=2).status_code, 201)

    def test_sales_window(self):
        _, early = new_event(self.org.user, sales_end=timezone.now() - timedelta(hours=1),
                             sales_start=timezone.now() - timedelta(days=2))
        self.assertEqual(checkout(new_buyer(), early).status_code, 409)  # early bird is over
        _, later = new_event(self.org.user, sales_start=timezone.now() + timedelta(days=1))
        self.assertEqual(checkout(new_buyer(), later).status_code, 409)  # not started yet

    def test_stopped_tier_cannot_be_bought(self):
        _, tt = new_event(self.org.user, on_sale=False)
        self.assertEqual(checkout(new_buyer(), tt).status_code, 409)

    def test_paused_then_resumed(self):
        event, tt = new_event(self.org.user)
        self.assertEqual(self.org.post(f"/api/organizer/events/{event.id}/pause").status_code, 200)
        r = checkout(new_buyer(), tt)
        self.assertEqual(r.status_code, 409)
        self.assertIn("paused", r.json()["detail"])
        self.assertEqual(self.org.post(f"/api/organizer/events/{event.id}/resume").status_code, 200)
        self.assertEqual(checkout(new_buyer(), tt).status_code, 201)

    def test_event_that_has_ended(self):
        event, tt = new_event(self.org.user)
        Event.objects.filter(pk=event.pk).update(starts_at=timezone.now() - timedelta(hours=5),
                                                 ends_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(checkout(new_buyer(), tt).status_code, 409)
        self.assertEqual(Event.objects.get(pk=event.pk).status, "ended")


class HiddenTierTests(EventTestCase):
    def setUp(self):
        super().setUp()
        self.event, _ = new_event(self.org.user)
        r = self.org.post(f"/api/organizer/events/{self.event.id}/ticket-types",
                          {"name": "Sponsors", "price": 0, "capacity": 20, "visibility": "hidden",
                           "access_code": "SPONSOR-2026"})
        self.assertEqual(r.status_code, 201, r.content)
        self.hidden = TicketType.objects.get(event=self.event, name="Sponsors")

    def test_hidden_tier_needs_a_code(self):
        r = self.org.post(f"/api/organizer/events/{self.event.id}/ticket-types",
                          {"name": "Guests", "price": 0, "capacity": 5, "visibility": "hidden"})
        self.assertEqual(r.status_code, 400)

    def test_code_is_stored_hashed(self):
        self.assertNotIn("SPONSOR", self.hidden.access_code_hash)
        self.assertTrue(self.hidden.access_code_hash.startswith("argon2$"))

    def test_hidden_tier_not_listed_publicly(self):
        names = [t["name"] for t in Browser().get(f"/api/events/{self.event.id}").json()["ticket_types"]]
        self.assertEqual(names, ["Regular"])

    def test_unlock_and_buy_with_code(self):
        b = new_buyer()
        self.assertEqual(b.post(f"/api/events/{self.event.id}/unlock", {"code": "wrong"}).status_code, 404)
        r = b.post(f"/api/events/{self.event.id}/unlock", {"code": "sponsor-2026"})  # not case-sensitive
        self.assertEqual([t["name"] for t in r.json()["ticket_types"]], ["Sponsors"])
        self.assertEqual(checkout(b, self.hidden, quantity=1).status_code, 404)  # no code
        self.assertEqual(checkout(b, self.hidden, quantity=1, access_code="nope").status_code, 404)
        self.assertEqual(checkout(b, self.hidden, quantity=1, access_code="SPONSOR-2026").status_code, 201)

    def test_code_guessing_is_rate_limited(self):
        b = Browser()
        codes = [b.post(f"/api/events/{self.event.id}/unlock", {"code": f"GUESS{i}"}).status_code for i in range(11)]
        self.assertEqual(codes[-1], 429)


class CancelAndRefundTests(EventTestCase):
    def test_cancel_refunds_paid_orders_and_releases_holds(self):
        event, tt = new_event(self.org.user, capacity=10)
        paid_buyer = new_buyer()
        paid_id = checkout(paid_buyer, tt).json()["id"]
        paid_buyer.post(f"/api/dev/orders/{paid_id}/pay", {"decision": "approve"})
        pending_id = checkout(new_buyer(), tt).json()["id"]
        token = Ticket.objects.filter(order_id=paid_id).first().token

        r = self.org.post(f"/api/organizer/events/{event.id}/cancel")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["refunds"], {"refunds_started": 1, "refunded": 1, "holds_released": 1})
        self.assertEqual(Order.objects.get(pk=paid_id).status, "refunded")
        self.assertEqual(Order.objects.get(pk=pending_id).status, "failed")
        self.assertTrue(AuditEntry.objects.filter(action="order.refunded", target=f"order:{paid_id}").exists())
        # A refunded ticket no longer gets anyone in.
        self.assertEqual(self.org.post("/api/organizer/checkin", {"token": token}).json()["result"], "invalid")
        # And the event can't be bought or edited any more.
        self.assertEqual(checkout(new_buyer(), tt).status_code, 409)
        r = self.patch(f"/api/organizer/events/{event.id}", {"title": "Back on"})
        self.assertEqual(r.status_code, 409)


@override_settings(MEDIA_ROOT=None)
class CoverImageTests(EventTestCase):
    def setUp(self):
        super().setUp()
        import tempfile

        self._media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self._media.name)
        self.settings_override.enable()
        self.eid = self.draft()

    def tearDown(self):
        self.settings_override.disable()
        self._media.cleanup()

    def upload(self, content, name="poster.png"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile(name, content, content_type="image/png")
        return self.org.client.post(f"/api/organizer/events/{self.eid}/cover", {"image": f},
                                    format="multipart", HTTP_X_CSRFTOKEN=self.org.csrf_token)

    def test_valid_image_is_reencoded_as_jpeg(self):
        r = self.upload(png_bytes())
        self.assertEqual(r.status_code, 200, r.content)
        event = Event.objects.get(pk=self.eid)
        self.assertTrue(event.cover_image.name.endswith(".jpg"))
        self.assertNotIn("poster", event.cover_image.name)  # uploader's filename not used
        with event.cover_image.open("rb") as fh:
            self.assertEqual(Image.open(fh).format, "JPEG")

    def test_fake_image_rejected(self):
        r = self.upload(b"<script>alert(1)</script>", name="evil.png")
        self.assertEqual(r.status_code, 400)
        r = self.upload(b"%PDF-1.4 not an image", name="doc.jpg")
        self.assertEqual(r.status_code, 400)

    def test_draft_cover_is_private(self):
        self.upload(png_bytes())
        self.assertEqual(self.org.get(f"/api/events/{self.eid}/cover").status_code, 200)
        self.assertEqual(Browser().get(f"/api/events/{self.eid}/cover").status_code, 404)
