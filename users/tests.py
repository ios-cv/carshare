from django.urls import reverse
from users.forms import AddMobileForm, VerifyMobileForm
from test_support import factories as f
from test_support.cases import FrozenTestCase


class UserEligibilityTests(FrozenTestCase):
    def test_no_mobile_prevents_booking(self):
        person = f.user(mobile=None)
        f.account(person)
        self.assertFalse(person.can_make_bookings())

    def test_booking_membership_is_distinct_from_driving(self):
        owner = f.user()
        account = f.account(owner)
        person = f.user()
        f.member(account, person, can_book=True)
        self.assertTrue(person.can_make_bookings())
        self.assertFalse(person.can_drive())
        f.profile(person)
        self.assertTrue(person.can_access_bookings())

    def test_readonly_member_cannot_make_bookings(self):
        owner = f.user()
        account = f.account(owner)
        person = f.user()
        f.member(account, person)
        self.assertTrue(person.can_view_bookings())
        self.assertFalse(person.can_make_bookings())

    def test_profile_expiry_at_booking_end(self):
        person = f.user()
        f.profile(person, expires_at=f.NOW)
        self.assertFalse(person.has_valid_driver_profile(at=f.NOW))

    def test_wrong_mobile_code_preserves_pending_number(self):
        person = f.user(pending_mobile="07700000001", mobile_verification_code="123456")
        form = VerifyMobileForm({"mobile_verification_code": "654321"}, instance=person)
        self.assertFalse(form.is_valid())
        person.refresh_from_db()
        self.assertEqual(person.pending_mobile, "07700000001")

    def test_mobile_verification_promotes_number_and_clears_code(self):
        person = f.user(pending_mobile="07700000001", mobile_verification_code="123456")
        form = VerifyMobileForm({"mobile_verification_code": "123456"}, instance=person)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        person.refresh_from_db()
        self.assertEqual(person.mobile, "07700000001")
        self.assertIsNone(person.mobile_verification_code)
        self.assertIsNone(person.pending_mobile)

    def test_add_mobile_does_not_verify_it(self):
        person = f.user(mobile=None)
        form = AddMobileForm({"pending_mobile": "07700000001"}, instance=person)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        person.refresh_from_db()
        self.assertIsNone(person.mobile)
        self.assertEqual(len(person.mobile_verification_code), 6)

    def test_signup_page_renders_without_network(self):
        self.assertEqual(self.client.get(reverse("account_signup")).status_code, 200)
