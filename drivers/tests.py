from datetime import timedelta
from backoffice.forms import DriverProfileApprovalForm
from test_support import factories as f
from test_support.cases import FrozenTestCase


class DriverApprovalTests(FrozenTestCase):
    def test_orm_profile_keeps_polymorphic_metadata(self):
        person = f.user()
        p = f.profile(person)
        self.assertEqual(
            person.driver_profiles.get().get_real_instance_class(), type(p)
        )

    def test_licence_expiry_caps_approval(self):
        p = f.profile(f.user(), licence_expiry_date=(f.NOW + timedelta(days=30)).date())
        form = DriverProfileApprovalForm(
            p, {"expiry": (f.NOW + timedelta(days=31)).date()}
        )
        self.assertFalse(form.is_valid())

    def test_annual_limit_caps_approval(self):
        p = f.profile(
            f.user(), licence_expiry_date=(f.NOW + timedelta(days=730)).date()
        )
        form = DriverProfileApprovalForm(
            p, {"expiry": (f.NOW + timedelta(days=367)).date()}
        )
        self.assertFalse(form.is_valid())

    def test_missing_review_prevents_readiness(self):
        p = f.profile(f.user())
        self.assertFalse(p.can_profile_be_approved())

    def test_expired_profile_does_not_grant_driving(self):
        person = f.user()
        f.profile(person, expires_at=f.NOW - timedelta(seconds=1))
        self.assertFalse(person.can_drive())
