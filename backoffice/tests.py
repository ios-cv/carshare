from django.urls import reverse
from test_support import factories as f
from test_support.cases import FrozenTestCase


class BackofficePermissionsTests(FrozenTestCase):
    def setUp(self):
        super().setUp()
        self.owner = f.user()
        self.account = f.account(self.owner)
        self.profile = f.profile(self.owner)
        self.car = f.vehicle()
        self.booking = f.booking(self.owner, self.car, self.account)

    def urls(self):
        return [
            reverse(name, args=args)
            for name, args in [
                ("backoffice_home", []),
                ("backoffice_bookings", []),
                ("backoffice_users", []),
                ("backoffice_accounts", []),
                ("backoffice_approvals", []),
                ("backoffice_vehicles", []),
                ("backoffice_user_details", [self.owner.pk]),
                ("backoffice_add_card", [self.owner.pk]),
                ("backoffice_edit_po", [self.owner.pk, self.account.pk]),
                ("backoffice_review_driver_profile", [self.profile.pk]),
                ("backoffice_approve_driver_profile", [self.profile.pk]),
                ("backoffice_approve_billing_account", [self.account.pk]),
                ("backoffice_reject_billing_account", [self.account.pk]),
                ("backoffice_close_booking", [self.booking.pk]),
                ("backoffice_lock_car", [self.car.pk]),
                ("backoffice_unlock_car", [self.car.pk]),
            ]
        ]

    def test_anonymous_cannot_access_any_backoffice_route(self):
        for url in self.urls():
            with self.subTest(url=url):
                self.assertRedirects(
                    self.client.get(url),
                    reverse("account_login"),
                    fetch_redirect_response=False,
                )

    def test_staff_superuser_and_ordinary_users_need_operator_flag(self):
        for flags in [{}, {"is_staff": True}, {"is_superuser": True, "is_staff": True}]:
            self.client.force_login(f.user(**flags))
            for url in self.urls():
                with self.subTest(flags=flags, url=url):
                    self.assertRedirects(
                        self.client.get(url),
                        reverse("bookings_history"),
                        fetch_redirect_response=False,
                    )
        self.account.refresh_from_db()
        self.assertIsNotNone(self.account.approved_at)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.state, "pending")
        from hardware.models import BoxAction

        self.assertFalse(BoxAction.objects.exists())

    def test_operator_can_open_dashboard_and_user_details(self):
        self.client.force_login(f.user(is_operator=True))
        for name, args in [
            ("backoffice_home", []),
            ("backoffice_users", []),
            ("backoffice_user_details", [self.owner.pk]),
        ]:
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse(name, args=args)).status_code, 200
                )
