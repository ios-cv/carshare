"""Tests for the billing app."""
import datetime
import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from billing.pricing import (
    calculate_booking_cost,
    DAY_RATE_2024,
    HOUR_RATE_2024,
    DAY_RATE_2026,
    HOUR_RATE_2026,
    TIME_CUTOFF_2026,
    ID_CUTOFF_2026,
)
from billing.models import (
    BillingAccount,
    BillingAccountMember,
    BillingAccountMemberInvitation,
    get_personal_billing_account_for_user,
    get_all_pending_approval,
    get_billing_accounts_suitable_for_booking,
)
from billing.forms import BusinessBillingAccountForm, InviteMemberForm
from billing.tasks import last_month, invoice_line_text


# ── Pricing tests (no DB) ────────────────────────────────────────────────────

def _mock_user(is_operator=False):
    u = MagicMock()
    u.is_operator = is_operator
    return u


def _mock_vehicle():
    return MagicMock()


def _mock_booking(booking_id):
    b = MagicMock()
    b.id = booking_id
    return b


def _mock_billing_account(ba_id):
    ba = MagicMock()
    ba.id = ba_id
    return ba


def test_operator_pays_zero():
    start = TIME_CUTOFF_2026 + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=2)
    assert calculate_booking_cost(_mock_user(is_operator=True), _mock_vehicle(), start, end) == 0


def test_legacy_rate_old_booking():
    start = datetime.datetime(2025, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(hours=2)
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end)
    expected = 0 * DAY_RATE_2024 + min(DAY_RATE_2024, 2 * HOUR_RATE_2024)
    assert cost == expected


def test_new_rate_booking_no_booking_obj():
    """When booking=None and start >= cutover, new rates apply."""
    start = TIME_CUTOFF_2026 + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=2)
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end, booking=None)
    expected = 0 * DAY_RATE_2026 + min(DAY_RATE_2026, 2 * HOUR_RATE_2026)
    assert cost == expected


def test_legacy_rate_low_id():
    """booking.id < ID_CUTOFF but start >= cutover → legacy rates."""
    start = TIME_CUTOFF_2026 + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=2)
    booking = _mock_booking(ID_CUTOFF_2026 - 1)
    ba = _mock_billing_account(1)  # not special
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end,
                                  billing_account=ba, booking=booking)
    expected = 0 * DAY_RATE_2024 + min(DAY_RATE_2024, 2 * HOUR_RATE_2024)
    assert cost == expected


def test_new_rate_high_id():
    """booking.id >= ID_CUTOFF and start >= cutover → new rates."""
    start = TIME_CUTOFF_2026 + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=2)
    booking = _mock_booking(ID_CUTOFF_2026)
    ba = _mock_billing_account(1)
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end,
                                  billing_account=ba, booking=booking)
    expected = 0 * DAY_RATE_2026 + min(DAY_RATE_2026, 2 * HOUR_RATE_2026)
    assert cost == expected


def test_special_billing_account_gets_new_rate():
    """Special billing account (id=29) + start >= cutover → new rates regardless of booking id."""
    start = TIME_CUTOFF_2026 + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(hours=2)
    booking = _mock_booking(ID_CUTOFF_2026 - 1)  # low id
    ba = _mock_billing_account(29)
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end,
                                  billing_account=ba, booking=booking)
    expected = 0 * DAY_RATE_2026 + min(DAY_RATE_2026, 2 * HOUR_RATE_2026)
    assert cost == expected


def test_day_rate_applied():
    """1 day + 2 hours uses day_rate for full day and min(day_rate, 2*hour_rate) for the remainder."""
    start = datetime.datetime(2025, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(days=1, hours=2)
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end)
    expected = 1 * DAY_RATE_2024 + min(DAY_RATE_2024, 2 * HOUR_RATE_2024)
    assert cost == expected


def test_zero_duration():
    start = datetime.datetime(2025, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
    end = start
    cost = calculate_booking_cost(_mock_user(), _mock_vehicle(), start, end)
    assert cost == 0


# ── BillingAccount.valid ─────────────────────────────────────────────────────

@pytest.mark.django_db
def test_valid_no_stripe_id(make_billing_account):
    ba = make_billing_account(approved=True, stripe_customer_id=None)
    assert ba.valid is False


@pytest.mark.django_db
def test_valid_empty_stripe_id(make_billing_account):
    ba = make_billing_account(approved=True, stripe_customer_id="")
    assert ba.valid is False


@pytest.mark.django_db
def test_valid_not_approved(make_billing_account):
    ba = make_billing_account(approved=False, stripe_customer_id="cus_1",
                               stripe_setup_intent_active=True)
    assert ba.valid is False


@pytest.mark.django_db
def test_valid_credit_account_bypass(make_billing_account):
    ba = make_billing_account(approved=True, stripe_customer_id="cus_1",
                               credit_account=True, stripe_setup_intent_active=False)
    assert ba.valid is True


@pytest.mark.django_db
def test_valid_no_setup_intent(make_billing_account):
    ba = make_billing_account(approved=True, stripe_customer_id="cus_1",
                               stripe_setup_intent_active=False)
    assert ba.valid is False


@pytest.mark.django_db
def test_valid_all_good(make_billing_account):
    ba = make_billing_account(approved=True, stripe_customer_id="cus_1",
                               stripe_setup_intent_active=True)
    assert ba.valid is True


# ── BillingAccount model properties ─────────────────────────────────────────

@pytest.mark.django_db
def test_display_name_personal(make_billing_account):
    ba = make_billing_account(account_type="p")
    assert ba.display_name == "Personal Billing Account"


@pytest.mark.django_db
def test_display_name_business(make_billing_account):
    ba = make_billing_account(account_type="b", account_name="ACME Corp")
    assert ba.display_name == "ACME Corp"


@pytest.mark.django_db
def test_driver_profile_python_type_full(make_billing_account):
    from drivers.models import FullDriverProfile
    ba = make_billing_account(driver_profile_type="f")
    assert ba.driver_profile_python_type is FullDriverProfile


@pytest.mark.django_db
def test_driver_profile_python_type_external(make_billing_account):
    from drivers.models import ExternalDriverProfile
    ba = make_billing_account(driver_profile_type="e")
    assert ba.driver_profile_python_type is ExternalDriverProfile


@pytest.mark.django_db
def test_driver_profile_python_type_unknown_raises(make_billing_account):
    ba = make_billing_account()
    ba.driver_profile_type = "x"
    with pytest.raises(Exception):
        _ = ba.driver_profile_python_type


@pytest.mark.django_db
def test_approve_sets_approved_at(make_billing_account):
    ba = make_billing_account(approved=False)
    assert ba.approved_at is None
    ba.approve()
    assert ba.approved_at is not None


@pytest.mark.django_db
def test_complete_property(make_billing_account):
    ba = make_billing_account(stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    assert ba.complete is True
    ba2 = make_billing_account(stripe_customer_id=None)
    assert not ba2.complete


# ── get_personal_billing_account_for_user ────────────────────────────────────

@pytest.mark.django_db
def test_get_personal_billing_account_returns_account(make_user, make_billing_account):
    user = make_user()
    ba = make_billing_account(owner=user, account_type="p")
    result = get_personal_billing_account_for_user(user)
    assert result == ba


@pytest.mark.django_db
def test_get_personal_billing_account_returns_none(make_user):
    user = make_user()
    result = get_personal_billing_account_for_user(user)
    assert result is None


# ── get_all_pending_approval ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_get_all_pending_approval_includes_business(make_billing_account):
    ba = make_billing_account(account_type="b", stripe_customer_id="cus_1",
                               stripe_setup_intent_active=True, approved=False)
    result = get_all_pending_approval()
    assert ba in result


@pytest.mark.django_db
def test_get_all_pending_approval_personal_with_valid_dp(
        make_user, make_billing_account, make_full_driver_profile):
    user = make_user(mobile="07700000001")
    ba = make_billing_account(owner=user, account_type="p",
                               stripe_customer_id="cus_2",
                               stripe_setup_intent_active=True, approved=False)
    make_full_driver_profile(user=user, approved=True)
    result = get_all_pending_approval()
    assert ba in result


@pytest.mark.django_db
def test_get_all_pending_approval_personal_without_valid_dp(
        make_user, make_billing_account):
    user = make_user()
    ba = make_billing_account(owner=user, account_type="p",
                               stripe_customer_id="cus_3",
                               stripe_setup_intent_active=True, approved=False)
    result = get_all_pending_approval()
    assert ba not in result


# ── get_billing_accounts_suitable_for_booking ────────────────────────────────

@pytest.mark.django_db
def test_suitable_for_booking_owner(make_user, make_billing_account):
    user = make_user()
    ba = make_billing_account(owner=user, approved=True,
                               stripe_customer_id="cus_x",
                               stripe_setup_intent_active=True)
    end = timezone.now() + timezone.timedelta(hours=2)
    result = list(get_billing_accounts_suitable_for_booking(user, end))
    assert ba in result


@pytest.mark.django_db
def test_suitable_for_booking_member_with_permission(make_user, make_billing_account):
    owner = make_user()
    member_user = make_user()
    ba = make_billing_account(owner=owner, approved=True,
                               stripe_customer_id="cus_y",
                               stripe_setup_intent_active=True)
    BillingAccountMember.objects.create(
        user=member_user,
        billing_account=ba,
        can_make_bookings=True,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    end = timezone.now() + timezone.timedelta(hours=2)
    result = list(get_billing_accounts_suitable_for_booking(member_user, end))
    assert ba in result


@pytest.mark.django_db
def test_suitable_for_booking_unapproved_excluded(make_user, make_billing_account):
    user = make_user()
    ba = make_billing_account(owner=user, approved=False,
                               stripe_customer_id="cus_z",
                               stripe_setup_intent_active=True)
    end = timezone.now() + timezone.timedelta(hours=2)
    result = list(get_billing_accounts_suitable_for_booking(user, end))
    assert ba not in result


# ── billing tasks helpers ─────────────────────────────────────────────────────

def test_last_month_returns_end_of_previous_month():
    import datetime as dt
    from django.utils import timezone as tz
    # May 15 → end of April
    now = dt.datetime(2025, 5, 15, tzinfo=dt.timezone.utc)
    result = last_month(now)
    assert result.month == 4
    assert result.day == 30


def test_invoice_line_text():
    booking = MagicMock()
    booking.id = 42
    booking.reservation_time.lower = datetime.datetime(2025, 5, 1, 10, 0, tzinfo=datetime.timezone.utc)
    booking.reservation_time.upper = datetime.datetime(2025, 5, 1, 12, 0, tzinfo=datetime.timezone.utc)
    booking.user.first_name = "Alice"
    booking.user.last_name = "Smith"
    booking.vehicle.registration = "AB12CDE"
    text = invoice_line_text(booking)
    assert "000042" in text
    assert "Alice Smith" in text
    assert "AB12CDE" in text


# ── billing views ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_create_billing_account_unauthenticated():
    client = Client()
    url = reverse("billing_create_account", kwargs={"billing_account_type": "personal"})
    response = client.get(url)
    assert response.status_code == 302
    assert "/login" in response["Location"]


@pytest.mark.django_db
@patch("billing.views.stripe.Customer.create")
def test_create_personal_billing_account_creates_and_redirects(mock_stripe, make_user):
    mock_stripe.return_value = MagicMock(id="cus_new")
    client = Client()
    user = make_user(mobile="07700000001")
    client.force_login(user)
    url = reverse("billing_create_account", kwargs={"billing_account_type": "personal"})
    response = client.get(url)
    assert response.status_code == 302
    assert BillingAccount.objects.filter(owner=user, account_type="p").exists()


@pytest.mark.django_db
def test_profile_manage_members_non_owner_redirected(make_user, make_billing_account):
    owner = make_user()
    other = make_user()
    ba = make_billing_account(owner=owner)
    client = Client()
    client.force_login(other)
    url = reverse("billing_account_members", kwargs={"billing_account": ba.id})
    response = client.get(url)
    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_manage_members_owner_gets_200(make_user, make_billing_account):
    owner = make_user()
    ba = make_billing_account(owner=owner)
    client = Client()
    client.force_login(owner)
    url = reverse("billing_account_members", kwargs={"billing_account": ba.id})
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_accept_invitation_owner_cannot_accept(make_user, make_billing_account):
    owner = make_user()
    ba = make_billing_account(owner=owner)
    invite = BillingAccountMemberInvitation.objects.create(
        inviting_user=owner,
        billing_account=ba,
        email=owner.email,
        secret=uuid.uuid4(),
        created_at=timezone.now(),
        can_make_bookings=False,
    )
    client = Client()
    client.force_login(owner)
    url = reverse("billing_account_accept_invitation", kwargs={"invitation": str(invite.secret)})
    response = client.get(url)
    assert response.status_code == 302
    # invitation should NOT be consumed
    assert BillingAccountMemberInvitation.objects.filter(pk=invite.pk).exists()


@pytest.mark.django_db
def test_accept_invitation_creates_member(make_user, make_billing_account):
    owner = make_user()
    member_user = make_user()
    ba = make_billing_account(owner=owner)
    invite = BillingAccountMemberInvitation.objects.create(
        inviting_user=owner,
        billing_account=ba,
        email=member_user.email,
        secret=uuid.uuid4(),
        created_at=timezone.now(),
        can_make_bookings=True,
    )
    client = Client()
    client.force_login(member_user)
    url = reverse("billing_account_accept_invitation", kwargs={"invitation": str(invite.secret)})
    client.get(url)
    assert BillingAccountMember.objects.filter(user=member_user, billing_account=ba).exists()
    assert not BillingAccountMemberInvitation.objects.filter(pk=invite.pk).exists()


@pytest.mark.django_db
def test_profile_revoke_invitation(make_user, make_billing_account):
    owner = make_user()
    ba = make_billing_account(owner=owner)
    invite = BillingAccountMemberInvitation.objects.create(
        inviting_user=owner,
        billing_account=ba,
        email="other@example.com",
        secret=uuid.uuid4(),
        created_at=timezone.now(),
        can_make_bookings=False,
    )
    client = Client()
    client.force_login(owner)
    url = reverse("billing_account_members_invitation_revoke",
                  kwargs={"billing_account": ba.id, "invitation": invite.id})
    client.get(url)
    assert not BillingAccountMemberInvitation.objects.filter(pk=invite.pk).exists()


@pytest.mark.django_db
def test_profile_remove_member(make_user, make_billing_account):
    owner = make_user()
    member_user = make_user()
    ba = make_billing_account(owner=owner)
    member = BillingAccountMember.objects.create(
        user=member_user,
        billing_account=ba,
        can_make_bookings=False,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    client = Client()
    client.force_login(owner)
    url = reverse("billing_account_members_remove",
                  kwargs={"billing_account": ba.id, "member": member.id})
    client.get(url)
    assert not BillingAccountMember.objects.filter(pk=member.pk).exists()


# ── billing forms ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_business_billing_account_form_valid_vat(make_user):
    user = make_user()
    data = {
        "account_name": "My Co",
        "business_name": "My Company Ltd",
        "business_address_line_1": "1 Street",
        "business_postcode": "SW1A 1AA",
        "business_tax_id": "GB 123 456 789",
    }
    form = BusinessBillingAccountForm(user, data)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["business_tax_id"] == "GB123456789"


@pytest.mark.django_db
def test_business_billing_account_form_invalid_vat(make_user):
    user = make_user()
    data = {
        "account_name": "My Co",
        "business_name": "My Company Ltd",
        "business_address_line_1": "1 Street",
        "business_postcode": "SW1A 1AA",
        "business_tax_id": "INVALID",
    }
    form = BusinessBillingAccountForm(user, data)
    assert not form.is_valid()


@pytest.mark.django_db
def test_invite_member_form_save(make_user, make_billing_account):
    owner = make_user()
    ba = make_billing_account(owner=owner)
    data = {"email": "invited@example.com", "can_make_bookings": False}
    form = InviteMemberForm(ba, owner, data)
    assert form.is_valid(), form.errors
    invite = form.save()
    assert invite.secret is not None
    assert invite.created_at is not None
    assert invite.billing_account == ba
    assert invite.inviting_user == owner

