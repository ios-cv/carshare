from datetime import timedelta
from unittest import expectedFailure

from django.urls import reverse
from hardware.models import Card, Telemetry
from hardware.tasks import remove_old_telemetry
from test_support import factories as f
from test_support.cases import FrozenTestCase


class DeviceAPITests(FrozenTestCase):
    def setUp(self):
        super().setUp()
        self.person = f.user()
        self.account = f.account(self.person)
        f.profile(self.person)
        self.car = f.vehicle()
        self.box = self.car.box
        self.headers = {
            "HTTP_X_CARSHARE_BOX_ID": format(self.box.serial, "x"),
            "HTTP_X_CARSHARE_BOX_SECRET": str(self.box.secret),
        }

    def test_unauthenticated_requests_have_no_effect(self):
        response = self.client.post(
            reverse("api_v1_touch"), {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.box.refresh_from_db()
        self.assertTrue(self.box.locked)
        self.assertFalse(Telemetry.objects.exists())

    def test_wrong_device_secret_rejected(self):
        headers = {
            **self.headers,
            "HTTP_X_CARSHARE_BOX_SECRET": "00000000-0000-0000-0000-000000000000",
        }
        response = self.client.post(
            reverse("api_v1_telemetry"), {}, content_type="application/json", **headers
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Telemetry.objects.exists())

    def test_card_unlock_and_lock_update_same_booking_and_box(self):
        b = f.booking(
            self.person, self.car, self.account, start=f.NOW - timedelta(minutes=5)
        )
        Card.objects.create(key="1", user=self.person)
        response = self.client.post(
            reverse("api_v1_touch"),
            {"card_id": "01000000"},
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.json()["action"], "unlock")
        b.refresh_from_db()
        self.box.refresh_from_db()
        self.assertEqual(b.state, "active")
        self.assertEqual(self.box.current_booking, b)
        response = self.client.post(
            reverse("api_v1_touch"),
            {"card_id": "01000000"},
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.json()["action"], "lock")
        b.refresh_from_db()
        self.box.refresh_from_db()
        self.assertEqual(b.state, "inactive")
        self.assertIsNone(self.box.current_booking)

    def test_unrelated_card_cannot_unlock(self):
        f.booking(
            self.person, self.car, self.account, start=f.NOW - timedelta(minutes=5)
        )
        Card.objects.create(key="1", user=f.user())
        response = self.client.post(
            reverse("api_v1_touch"),
            {"card_id": "01000000"},
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.json()["action"], "reject")
        self.box.refresh_from_db()
        self.assertTrue(self.box.locked)

    def test_telemetry_is_associated_with_authenticated_box(self):
        response = self.client.post(
            reverse("api_v1_telemetry"),
            {"telemetry": {"soc_percent": 85}},
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Telemetry.objects.get().box, self.box)
        self.assertEqual(Telemetry.objects.get().soc_percent, 85)

    def test_retention_preserves_boundary_and_newer_data(self):
        old = Telemetry.objects.create(box=self.box)
        edge = Telemetry.objects.create(box=self.box)
        Telemetry.objects.filter(pk=old.pk).update(
            created_at=f.NOW - timedelta(days=181)
        )
        Telemetry.objects.filter(pk=edge.pk).update(
            created_at=f.NOW - timedelta(days=180)
        )
        remove_old_telemetry.run()
        remove_old_telemetry.run()
        self.assertFalse(Telemetry.objects.filter(pk=old.pk).exists())
        self.assertTrue(Telemetry.objects.filter(pk=edge.pk).exists())

    @expectedFailure
    def test_disabled_card_cannot_unlock_known_gap(self):
        # Main ignores Card.enabled. Remove expectedFailure after the production fix.
        f.booking(
            self.person, self.car, self.account, start=f.NOW - timedelta(minutes=5)
        )
        Card.objects.create(key="1", user=self.person, enabled=False)
        response = self.client.post(
            reverse("api_v1_touch"),
            {"card_id": "01000000"},
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(response.json()["action"], "reject")
