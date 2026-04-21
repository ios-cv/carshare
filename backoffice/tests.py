"""Tests for the backoffice app."""
import datetime
import uuid

import pytest
from unittest.mock import patch, MagicMock

from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from backoffice.decorators import require_backoffice_access
from backoffice.forms import DriverProfileApprovalForm, CloseBookingForm
from backoffice.templatetags.user_utils import can_drive_full, can_drive_external
from bookings.models import Booking
from drivers.models import FullDriverProfile


# ── Decorator tests ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_require_backoffice_anonymous():
    client = Client()
    url = reverse("backoffice_home")
    response = client.get(url)
    assert response.status_code == 302
    assert "login" in response["Location"]


@pytest.mark.django_db
def test_require_backoffice_non_operator(make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    url = reverse("backoffice_home")
    response = client.get(url)
    assert response.status_code == 302
    assert "history" in response["Location"]


@pytest.mark.django_db
def test_require_backoffice_operator(make_operator_user):
    user = make_operator_user()
    client = Client()
    client.force_login(user)
    url = reverse("backoffice_home")
    response = client.get(url)
    assert response.status_code == 200


# ── Backoffice views ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_backoffice_bookings_renders(make_operator_user):
    user = make_operator_user()
    client = Client()
    client.force_login(user)
    url = reverse("backoffice_bookings")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_backoffice_users_renders(make_operator_user):
    user = make_operator_user()
    client = Client()
    client.force_login(user)
    url = reverse("backoffice_users")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_backoffice_approvals_renders(make_operator_user):
    user = make_operator_user()
    client = Client()
    client.force_login(user)
    url = reverse("backoffice_approvals")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@patch("backoffice.views.EmailMessage.send")
def test_approve_billing_account(mock_send, make_operator_user, make_user, make_billing_account):
    operator = make_operator_user()
    owner = make_user()
    ba = make_billing_account(owner=owner, approved=False)
    client = Client()
    client.force_login(operator)
    url = reverse("backoffice_approve_billing_account", kwargs={"id": ba.id})
    response = client.get(url)
    assert response.status_code == 302
    ba.refresh_from_db()
    assert ba.approved_at is not None


@pytest.mark.django_db
def test_reject_billing_account(make_operator_user, make_user, make_billing_account):
    operator = make_operator_user()
    owner = make_user()
    ba = make_billing_account(owner=owner)
    ba_id = ba.id
    client = Client()
    client.force_login(operator)
    url = reverse("backoffice_reject_billing_account", kwargs={"id": ba_id})
    response = client.get(url)
    assert response.status_code == 302
    from billing.models import BillingAccount
    assert not BillingAccount.objects.filter(pk=ba_id).exists()


@pytest.mark.django_db
def test_close_booking_not_started(make_operator_user, make_booking):
    operator = make_operator_user()
    # Booking starts in the future
    start = timezone.now() + timezone.timedelta(hours=2)
    end = start + timezone.timedelta(hours=2)
    b = make_booking(start=start, end=end, state=Booking.STATE_PENDING)
    client = Client()
    client.force_login(operator)
    url = reverse("backoffice_close_booking", kwargs={"booking_id": b.id})
    response = client.get(url)
    assert response.status_code == 302
    b.refresh_from_db()
    assert b.state == Booking.STATE_PENDING  # unchanged


@pytest.mark.django_db
def test_close_booking_success(make_operator_user, make_booking):
    operator = make_operator_user()
    # Booking started in the past
    start = timezone.now() - timezone.timedelta(hours=1)
    end = timezone.now() + timezone.timedelta(hours=1)
    b = make_booking(start=start, end=end, state=Booking.STATE_ACTIVE)
    client = Client()
    client.force_login(operator)
    url = reverse("backoffice_close_booking", kwargs={"booking_id": b.id})
    response = client.get(url)
    assert response.status_code == 302
    b.refresh_from_db()
    assert b.state == Booking.STATE_INACTIVE


@pytest.mark.django_db
def test_add_card_get(make_operator_user, make_user):
    operator = make_operator_user()
    target_user = make_user()
    client = Client()
    client.force_login(operator)
    url = reverse("backoffice_add_card", kwargs={"id": target_user.id})
    response = client.get(url)
    assert response.status_code == 200


# ── Backoffice forms ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_driver_profile_approval_form_expiry_past_licence(make_user):
    user = make_user()
    dp = FullDriverProfile.create(user)
    dp.licence_expiry_date = (timezone.now() - timezone.timedelta(days=30)).date()
    dp.save()
    data = {"expiry": (timezone.now() - timezone.timedelta(days=1)).strftime("%Y-%m-%d")}
    form = DriverProfileApprovalForm(dp, data)
    assert not form.is_valid()


@pytest.mark.django_db
def test_driver_profile_approval_form_expiry_too_far(make_user):
    user = make_user()
    dp = FullDriverProfile.create(user)
    dp.licence_expiry_date = (timezone.now() + timezone.timedelta(days=730)).date()
    dp.save()
    too_far = (timezone.now() + timezone.timedelta(days=400)).strftime("%Y-%m-%d")
    data = {"expiry": too_far}
    form = DriverProfileApprovalForm(dp, data)
    assert not form.is_valid()


@pytest.mark.django_db
def test_driver_profile_approval_form_valid(make_user, make_operator_user):
    operator = make_operator_user()
    user = make_user()
    dp = FullDriverProfile.create(user)
    dp.licence_expiry_date = (timezone.now() + timezone.timedelta(days=365)).date()
    dp.save()
    valid_expiry = (timezone.now() + timezone.timedelta(days=180)).strftime("%Y-%m-%d")
    data = {"expiry": valid_expiry}
    form = DriverProfileApprovalForm(dp, data)
    assert form.is_valid(), form.errors
    form.save(operator)
    dp.refresh_from_db()
    assert dp.approved_to_drive is True
    assert dp.approved_by == operator


def test_close_booking_form_defaults():
    form = CloseBookingForm({})
    assert form.is_valid()
    assert form.cleaned_data["should_lock"] is False


# ── Template tags ─────────────────────────────────────────────────────────────

def test_can_drive_full_tag():
    user = MagicMock()
    can_drive_full(user)
    user.can_drive.assert_called_once_with(profile_type=FullDriverProfile)


def test_can_drive_external_tag():
    user = MagicMock()
    can_drive_external(user)
    user.can_drive.assert_called_once_with(profile_type=ExternalDriverProfile)


# Import ExternalDriverProfile for the tag test
from drivers.models import ExternalDriverProfile

