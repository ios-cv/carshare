"""Tests for the drivers app."""
import datetime

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from drivers.models import (
    DriverProfile,
    FullDriverProfile,
    ExternalDriverProfile,
    get_all_pending_approval,
)


# ── DriverProfile.is_expired ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_is_expired_no_expiry(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.expires_at = None
    assert dp.is_expired() is False


@pytest.mark.django_db
def test_is_expired_past(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.expires_at = timezone.now() - timezone.timedelta(days=1)
    assert dp.is_expired() is True


@pytest.mark.django_db
def test_is_expired_future(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.expires_at = timezone.now() + timezone.timedelta(days=365)
    assert dp.is_expired() is False


@pytest.mark.django_db
def test_is_expired_at_parameter(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.expires_at = timezone.now() + timezone.timedelta(days=10)
    future_check = timezone.now() + timezone.timedelta(days=20)
    assert dp.is_expired(now=future_check) is True


# ── FullDriverProfile.create ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_full_driver_profile_create(make_user):
    user = make_user()
    dp = FullDriverProfile.create(user)
    assert dp.user == user
    assert dp.created_at is not None
    assert dp.updated_at is not None


# ── FullDriverProfile.get_incomplete_driver_profile ───────────────────────────

@pytest.mark.django_db
def test_get_incomplete_returns_most_recent(make_user):
    user = make_user()
    dp1 = FullDriverProfile.create(user)
    dp1.save()
    dp2 = FullDriverProfile.create(user)
    dp2.save()
    result = FullDriverProfile.get_incomplete_driver_profile(user)
    assert result == dp2


@pytest.mark.django_db
def test_get_incomplete_returns_none_when_none(make_user):
    user = make_user()
    result = FullDriverProfile.get_incomplete_driver_profile(user)
    assert result is None


# ── Approval group helpers ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_is_personal_details_approved_true(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    dp.approved_address = True
    dp.approved_date_of_birth = True
    assert dp.is_personal_details_approved() is True


@pytest.mark.django_db
def test_is_personal_details_approved_false(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    dp.approved_address = None
    dp.approved_date_of_birth = True
    assert not dp.is_personal_details_approved()


@pytest.mark.django_db
def test_can_profile_be_approved_all_true(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    dp.approved_address = True
    dp.approved_date_of_birth = True
    dp.approved_licence_number = True
    dp.approved_licence_issue_date = True
    dp.approved_licence_expiry_date = True
    dp.approved_licence_front = True
    dp.approved_licence_back = True
    dp.approved_licence_selfie = True
    dp.approved_proof_of_address = True
    dp.approved_driving_record = True
    assert dp.can_profile_be_approved() is True


@pytest.mark.django_db
def test_can_profile_be_approved_missing_one(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    dp.approved_address = True
    dp.approved_date_of_birth = True
    dp.approved_licence_number = True
    dp.approved_licence_issue_date = True
    dp.approved_licence_expiry_date = True
    dp.approved_licence_front = True
    dp.approved_licence_back = True
    dp.approved_licence_selfie = True
    dp.approved_proof_of_address = None  # missing
    dp.approved_driving_record = True
    assert not dp.can_profile_be_approved()


@pytest.mark.django_db
def test_is_anything_rejected_true(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = False  # REJECTED
    assert dp.is_anything_rejected() is True


@pytest.mark.django_db
def test_is_anything_rejected_false(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    assert not dp.is_anything_rejected()


@pytest.mark.django_db
def test_reset_personal_details_approvals(make_full_driver_profile):
    dp = make_full_driver_profile()
    dp.approved_full_name = True
    dp.approved_address = True
    dp.approved_date_of_birth = True
    dp.reset_personal_details_approvals()
    assert dp.approved_full_name is None
    assert dp.approved_address is None
    assert dp.approved_date_of_birth is None


@pytest.mark.django_db
def test_get_max_permitted_expiry_date_limited_by_one_year(make_full_driver_profile):
    dp = make_full_driver_profile()
    # Set licence expiry far in the future
    dp.licence_expiry_date = (timezone.now() + timezone.timedelta(days=730)).date()
    result = dp.get_max_permitted_expiry_date()
    one_year_from_now = timezone.now() + timezone.timedelta(days=365)
    assert result <= one_year_from_now + timezone.timedelta(seconds=2)


@pytest.mark.django_db
def test_get_max_permitted_expiry_limited_by_licence(make_full_driver_profile):
    dp = make_full_driver_profile()
    # Set licence expiry very soon
    expiry_date = (timezone.now() + timezone.timedelta(days=30)).date()
    dp.licence_expiry_date = expiry_date
    result = dp.get_max_permitted_expiry_date()
    expected = timezone.datetime.combine(
        expiry_date, timezone.datetime.max.time(), datetime.timezone.utc
    )
    assert result == expected


# ── get_all_pending_approval ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_all_pending_approval_includes_submitted(make_full_driver_profile):
    dp = make_full_driver_profile(submitted=True)
    result = list(get_all_pending_approval())
    ids = [r.id for r in result]
    assert dp.id in ids


@pytest.mark.django_db
def test_get_all_pending_approval_excludes_approved(make_full_driver_profile):
    dp = make_full_driver_profile(approved=True)
    result = list(get_all_pending_approval())
    ids = [r.id for r in result]
    assert dp.id not in ids


# ── drivers decorators ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_incomplete_driver_profile_required_no_profile_redirects(make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    url = reverse("drivers_build_profile", kwargs={"stage": 1})
    response = client.get(url)
    assert response.status_code == 302
    assert "create" in response["Location"]


@pytest.mark.django_db
def test_incomplete_driver_profile_required_with_profile(make_user):
    user = make_user()
    dp = FullDriverProfile.create(user)
    dp.save()
    client = Client()
    client.force_login(user)
    url = reverse("drivers_build_profile", kwargs={"stage": 1})
    response = client.get(url)
    # Should render the form (200), not redirect to create
    assert response.status_code == 200


# ── drivers views ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_profile_redirects_to_bookings_when_valid(make_user, make_full_driver_profile):
    user = make_user()
    # Create a valid profile expiring in more than 60 days
    dp = make_full_driver_profile(user=user, approved=True,
                                   expires_at=timezone.now() + timezone.timedelta(days=90))
    client = Client()
    client.force_login(user)
    url = reverse("drivers_create_profile")
    response = client.get(url)
    assert response.status_code == 302
    assert "bookings" in response["Location"]


@pytest.mark.django_db
def test_create_profile_no_profile_creates_and_redirects(make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    url = reverse("drivers_create_profile")
    response = client.get(url)
    assert response.status_code == 302
    assert FullDriverProfile.objects.filter(user=user).exists()

