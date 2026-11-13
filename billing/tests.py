from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import expectedFailure
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from billing.models import BillingAccount
from billing.pricing import calculate_booking_cost
from billing.tasks import run_billing, monthly_billing
from bookings.models import Booking
from test_support import factories as f
from test_support.cases import FrozenTestCase


class PricingTests(SimpleTestCase):
    def price(self, minutes, start=None, **kwargs):
        start = start or datetime(2026, 4, 1, tzinfo=timezone.utc)
        return calculate_booking_cost(
            SimpleNamespace(is_operator=False),
            None,
            start,
            start + timedelta(minutes=minutes),
            **kwargs
        )

    def test_independent_tariff_examples(self):
        for minutes, expected in [
            (30, 6),
            (60, 6),
            (61, 12),
            (360, 33),
            (1440, 33),
            (1500, 39),
        ]:
            with self.subTest(minutes=minutes):
                self.assertEqual(self.price(minutes), expected)

    def test_legacy_tariff_examples(self):
        for minutes, expected in [(30, 5), (61, 10), (360, 30), (1500, 35)]:
            with self.subTest(minutes=minutes):
                self.assertEqual(
                    self.price(
                        minutes, start=datetime(2025, 1, 1, tzinfo=timezone.utc)
                    ),
                    expected,
                )

    def test_existing_booking_id_boundary(self):
        self.assertEqual(self.price(60, booking=SimpleNamespace(id=8621)), 5)
        self.assertEqual(self.price(60, booking=SimpleNamespace(id=8622)), 6)

    def test_special_account_exception(self):
        self.assertEqual(
            self.price(
                60,
                booking=SimpleNamespace(id=1),
                billing_account=SimpleNamespace(id=29),
            ),
            6,
        )
        self.assertEqual(
            self.price(
                60,
                booking=SimpleNamespace(id=1),
                billing_account=SimpleNamespace(id=28),
            ),
            5,
        )

    def test_cutover_is_inclusive(self):
        cutoff = datetime(2026, 4, 1, tzinfo=timezone.utc)
        self.assertEqual(self.price(60, start=cutoff - timedelta(seconds=1)), 5)
        self.assertEqual(self.price(60, start=cutoff), 6)

    def test_operator_free(self):
        self.assertEqual(
            calculate_booking_cost(
                SimpleNamespace(is_operator=True),
                None,
                f.NOW,
                f.NOW + timedelta(days=2),
            ),
            0,
        )


class BillingTests(FrozenTestCase):
    def setUp(self):
        super().setUp()
        self.owner = f.user()
        self.account = f.account(self.owner)
        self.car = f.vehicle()

    def test_account_validity_matrix(self):
        for changes, expected in [
            ({}, True),
            ({"approved_at": None}, False),
            ({"stripe_customer_id": ""}, False),
            ({"stripe_setup_intent_active": False}, False),
            ({"stripe_setup_intent_active": False, "credit_account": True}, True),
        ]:
            with self.subTest(changes=changes):
                a = BillingAccount(
                    owner=self.owner,
                    account_type="p",
                    driver_profile_type="f",
                    approved_at=f.NOW,
                    stripe_customer_id="cus_test",
                    stripe_setup_intent_active=True,
                )
                for key, value in changes.items():
                    setattr(a, key, value)
                self.assertEqual(a.valid, expected)

    def test_non_owner_cannot_setup_payment(self):
        original_id = self.account.stripe_customer_id
        self.client.force_login(f.user())
        with patch("billing.views.stripe.Customer.create") as create:
            response = self.client.get(
                reverse("billing_set_payment", args=[self.account.pk])
            )
        self.assertEqual(response.status_code, 302)
        create.assert_not_called()
        self.account.refresh_from_db()
        self.assertEqual(self.account.stripe_customer_id, original_id)

    def test_setup_callback_rejects_foreign_customer(self):
        self.client.force_login(f.user())
        self.account.stripe_setup_intent_active = False
        self.account.save()
        with patch(
            "billing.views.stripe.SetupIntent.retrieve",
            return_value=SimpleNamespace(
                status="succeeded", customer=self.account.stripe_customer_id
            ),
        ):
            response = self.client.get(
                reverse("billing_setup_complete"), {"setup_intent": "seti_test"}
            )
        self.assertEqual(response.status_code, 302)
        self.account.refresh_from_db()
        self.assertFalse(self.account.stripe_setup_intent_active)

    def test_successful_setup_callback_completes_only_payment_setup(self):
        self.account.stripe_setup_intent_active = False
        self.account.approved_at = None
        self.account.save()
        self.client.force_login(self.owner)
        with patch(
            "billing.views.stripe.SetupIntent.retrieve",
            return_value=SimpleNamespace(
                status="succeeded", customer=self.account.stripe_customer_id
            ),
        ):
            response = self.client.get(
                reverse("billing_setup_complete"), {"setup_intent": "seti_test"}
            )
        self.assertRedirects(
            response, reverse("drivers_create_profile"), fetch_redirect_response=False
        )
        self.account.refresh_from_db()
        self.assertTrue(self.account.stripe_setup_intent_active)
        self.assertIsNone(self.account.approved_at)

    def test_unsuccessful_setup_callback_does_not_enable_payments(self):
        self.account.stripe_setup_intent_active = False
        self.account.save()
        self.client.force_login(self.owner)
        with patch(
            "billing.views.stripe.SetupIntent.retrieve",
            return_value=SimpleNamespace(
                status="requires_payment_method",
                customer=self.account.stripe_customer_id,
            ),
        ):
            response = self.client.get(
                reverse("billing_setup_complete"), {"setup_intent": "seti_test"}
            )
        self.assertEqual(response.status_code, 200)
        self.account.refresh_from_db()
        self.assertFalse(self.account.stripe_setup_intent_active)

    @patch(
        "billing.tasks.stripe.InvoiceItem.create",
        return_value=SimpleNamespace(id="ii_test"),
    )
    @patch(
        "billing.tasks.stripe.Invoice.create",
        return_value=SimpleNamespace(id="in_test"),
    )
    def test_ordinary_invoice_amount_and_repeated_run(self, invoice, item):
        b = f.booking(self.owner, self.car, self.account, state="ended")
        run_billing.run()
        run_billing.run()
        invoice.assert_called_once()
        item.assert_called_once()
        self.assertEqual(item.call_args.kwargs["amount"], 1000)
        self.assertEqual(item.call_args.kwargs["currency"], "gbp")
        self.assertEqual(
            item.call_args.kwargs["customer"], self.account.stripe_customer_id
        )
        b.refresh_from_db()
        self.assertEqual(b.state, "billed")
        self.assertEqual(b.stripe_invoice_item_id, "ii_test")

    @patch("billing.tasks.stripe.InvoiceItem.create")
    @patch("billing.tasks.stripe.Invoice.create")
    def test_pending_and_credit_bookings_not_ordinary_billed(self, invoice, item):
        b = f.booking(self.owner, self.car, self.account)
        run_billing.run()
        invoice.assert_not_called()
        self.account.credit_account = True
        self.account.save()
        b.state = "ended"
        b.save()
        run_billing.run()
        invoice.assert_not_called()
        item.assert_not_called()

    @patch("billing.tasks.stripe.Invoice.create")
    def test_operator_zero_cost_never_calls_stripe(self, invoice):
        self.owner.is_operator = True
        self.owner.save()
        b = f.booking(self.owner, self.car, self.account, state="ended")
        run_billing.run()
        invoice.assert_not_called()
        b.refresh_from_db()
        self.assertEqual(b.state, "billed")

    @patch("billing.tasks.stripe.Invoice.create", side_effect=RuntimeError("offline"))
    def test_provider_failure_keeps_booking_unbilled(self, invoice):
        b = f.booking(self.owner, self.car, self.account, state="ended")
        with self.assertRaises(RuntimeError):
            run_billing.run()
        b.refresh_from_db()
        self.assertEqual(b.state, "ended")
        self.assertIsNone(b.stripe_invoice_item_id)

    @patch(
        "billing.tasks.stripe.InvoiceItem.create",
        side_effect=RuntimeError("item failed"),
    )
    @patch(
        "billing.tasks.stripe.Invoice.create",
        return_value=SimpleNamespace(id="in_test"),
    )
    def test_item_failure_keeps_booking_unbilled(self, invoice, item):
        b = f.booking(self.owner, self.car, self.account, state="ended")
        with self.assertRaises(RuntimeError):
            run_billing.run()
        b.refresh_from_db()
        self.assertEqual(b.state, "ended")
        self.assertIsNone(b.stripe_invoice_item_id)

    @patch(
        "billing.tasks.stripe.InvoiceItem.create",
        return_value=SimpleNamespace(id="ii_test"),
    )
    @patch(
        "billing.tasks.stripe.Invoice.create",
        return_value=SimpleNamespace(id="in_test"),
    )
    def test_monthly_only_previous_month_credit_bookings(self, invoice, item):
        self.account.credit_account = True
        self.account.save()
        old = f.booking(
            self.owner,
            self.car,
            self.account,
            start=f.NOW - timedelta(days=30),
            end=f.NOW - timedelta(days=30) + timedelta(hours=2),
            state="ended",
        )
        recent = f.booking(self.owner, self.car, self.account, state="ended")
        monthly_billing.run()
        invoice.assert_called_once()
        item.assert_called_once()
        old.refresh_from_db()
        recent.refresh_from_db()
        self.assertEqual(old.state, "billed")
        self.assertEqual(recent.state, "ended")


class BillingRetryKnownGapTests(FrozenTestCase):
    @expectedFailure
    def test_partial_failure_retry_does_not_duplicate_invoice_known_gap(self):
        # Main creates a new invoice after an invoice-item failure. This test
        # expresses the desired invariant, not approval of duplicate drafts.
        owner = f.user()
        account = f.account(owner)
        car = f.vehicle()
        f.booking(owner, car, account, state="ended")
        with patch(
            "billing.tasks.stripe.Invoice.create",
            return_value=SimpleNamespace(id="in_test"),
        ) as invoice, patch(
            "billing.tasks.stripe.InvoiceItem.create",
            side_effect=[RuntimeError("item failed"), SimpleNamespace(id="ii_test")],
        ):
            with self.assertRaises(RuntimeError):
                run_billing.run()
            run_billing.run()
        self.assertEqual(invoice.call_count, 1)
