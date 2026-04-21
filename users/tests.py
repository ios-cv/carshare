"""Tests for the users app."""
import pytest
from unittest.mock import patch, MagicMock

from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from users.models import User
from users.forms import AddMobileForm, VerifyMobileForm
from users.adapter import AccountAdapter


# ── User model ────────────────────────────────────────────────────────────────

def test_generate_verification_code_length():
    code = User.generate_verification_code()
    assert len(code) == 6


def test_generate_verification_code_digits_only():
    code = User.generate_verification_code()
    assert code.isdigit()


@pytest.mark.django_db
def test_has_validated_mobile_true(make_user):
    user = make_user(mobile="07700000001")
    assert user.has_validated_mobile() is True


@pytest.mark.django_db
def test_has_validated_mobile_false(make_user):
    user = make_user()
    assert user.has_validated_mobile() is False


@pytest.mark.django_db
def test_mobile_validation_pending_true(make_user):
    user = make_user()
    user.pending_mobile = "07700000002"
    assert user.mobile_validation_pending() is True


@pytest.mark.django_db
def test_mobile_validation_pending_false(make_user):
    user = make_user()
    assert user.mobile_validation_pending() is False


@pytest.mark.django_db
def test_has_valid_driver_profile_no_profiles(make_user):
    user = make_user()
    assert user.has_valid_driver_profile() is False


@pytest.mark.django_db
def test_has_valid_driver_profile_expired(make_user, make_full_driver_profile):
    user = make_user()
    make_full_driver_profile(user=user, approved=True,
                             expires_at=timezone.now() - timezone.timedelta(days=1))
    # Manually expire
    user.driver_profiles.filter(approved_to_drive=True).update(
        expires_at=timezone.now() - timezone.timedelta(days=1)
    )
    assert user.has_valid_driver_profile() is False


@pytest.mark.django_db
def test_has_valid_driver_profile_valid(make_user, make_full_driver_profile):
    user = make_user()
    make_full_driver_profile(user=user, approved=True)
    assert user.has_valid_driver_profile() is True


@pytest.mark.django_db
def test_can_drive_no_mobile(make_user):
    user = make_user()
    assert user.can_drive() is False


@pytest.mark.django_db
def test_can_drive_no_dp(make_user):
    user = make_user(mobile="07700000001")
    assert user.can_drive() is False


@pytest.mark.django_db
def test_can_drive_valid(make_user, make_full_driver_profile):
    user = make_user(mobile="07700000001")
    make_full_driver_profile(user=user, approved=True)
    assert user.can_drive() is True


@pytest.mark.django_db
def test_can_make_bookings_false_no_mobile(make_user):
    user = make_user()
    assert user.can_make_bookings() is False


@pytest.mark.django_db
def test_can_make_bookings_true(make_user, make_billing_account, make_full_driver_profile):
    user = make_user(mobile="07700000001")
    make_billing_account(owner=user, account_type="p", approved=True,
                          stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    assert user.can_make_bookings() is True


@pytest.mark.django_db
def test_has_valid_billing_account_true(make_user, make_billing_account):
    user = make_user()
    make_billing_account(owner=user, approved=True,
                          stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    assert user.has_valid_billing_account() is True


@pytest.mark.django_db
def test_has_valid_billing_account_false(make_user):
    user = make_user()
    assert not user.has_valid_billing_account()


@pytest.mark.django_db
def test_is_own_personal_account_validated(make_user, make_billing_account,
                                            make_full_driver_profile):
    user = make_user(mobile="07700000001")
    make_billing_account(owner=user, account_type="p", approved=True,
                          stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    make_full_driver_profile(user=user, approved=True)
    assert user.is_own_personal_account_validated() is True


@pytest.mark.django_db
def test_is_own_personal_account_validated_false_no_dp(make_user, make_billing_account):
    user = make_user()
    make_billing_account(owner=user, account_type="p", approved=True,
                          stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    assert user.is_own_personal_account_validated() is False


@pytest.mark.django_db
def test_is_own_business_account_validated(make_user, make_billing_account,
                                            make_external_driver_profile):
    user = make_user(mobile="07700000001")
    make_billing_account(owner=user, account_type="b", driver_profile_type="e",
                          approved=True, stripe_customer_id="cus_biz",
                          stripe_setup_intent_active=True)
    make_external_driver_profile(user=user, approved=True)
    assert user.is_own_business_account_validated() is True


# ── AddMobileForm ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_add_mobile_form_save_sets_code(make_user):
    user = make_user()
    form = AddMobileForm({"pending_mobile": "07700000001"}, instance=user)
    assert form.is_valid(), form.errors
    saved = form.save(commit=False)
    assert saved.mobile_verification_code is not None
    assert len(saved.mobile_verification_code) == 6


@pytest.mark.django_db
def test_add_mobile_form_save_commit_false_no_db_save(make_user):
    user = make_user()
    form = AddMobileForm({"pending_mobile": "07700000001"}, instance=user)
    assert form.is_valid()
    form.save(commit=False)
    # User still has no mobile_verification_code in DB
    user.refresh_from_db()
    assert user.mobile_verification_code is None


# ── VerifyMobileForm ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_verify_mobile_form_correct_code(make_user):
    user = make_user()
    user.mobile_verification_code = "123456"
    user.pending_mobile = "07700000001"
    user.save()
    form = VerifyMobileForm({"mobile_verification_code": "123456"}, instance=user)
    assert form.is_valid(), form.errors


@pytest.mark.django_db
def test_verify_mobile_form_wrong_code(make_user):
    user = make_user()
    user.mobile_verification_code = "123456"
    user.pending_mobile = "07700000001"
    user.save()
    form = VerifyMobileForm({"mobile_verification_code": "999999"}, instance=user)
    assert not form.is_valid()


@pytest.mark.django_db
def test_verify_mobile_form_save_promotes_mobile(make_user):
    user = make_user()
    user.mobile_verification_code = "123456"
    user.pending_mobile = "07700000001"
    user.save()
    form = VerifyMobileForm({"mobile_verification_code": "123456"}, instance=user)
    assert form.is_valid()
    saved = form.save()
    assert saved.mobile == "07700000001"
    assert saved.pending_mobile is None
    assert saved.mobile_verification_code is None


# ── users decorators ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_require_incomplete_user_complete_redirects(make_user, make_billing_account,
                                                      make_full_driver_profile):
    user = make_user(mobile="07700000001")
    make_billing_account(owner=user, account_type="p", approved=True,
                          stripe_customer_id="cus_1", stripe_setup_intent_active=True)
    make_full_driver_profile(user=user, approved=True)
    client = Client()
    client.force_login(user)
    url = reverse("users_incomplete")
    response = client.get(url)
    assert response.status_code == 302
    assert "history" in response["Location"]


@pytest.mark.django_db
def test_require_user_can_make_bookings_redirects_if_cannot(make_user):
    user = make_user()  # no mobile
    client = Client()
    client.force_login(user)
    url = reverse("bookings_search")
    response = client.get(url)
    assert response.status_code == 302


# ── users views ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_add_mobile_get_authenticated(make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    url = reverse("users_mobile_add")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@patch("users.views.send_sms_verification_code")
def test_add_mobile_post_valid_redirects(mock_sms, make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    url = reverse("users_mobile_add")
    response = client.post(url, {"pending_mobile": "07700000001"})
    assert response.status_code == 302
    assert "verify" in response["Location"]
    mock_sms.assert_called_once()


@pytest.mark.django_db
def test_verify_mobile_get_authenticated(make_user):
    user = make_user()
    user.mobile_verification_code = "123456"
    user.pending_mobile = "07700000001"
    user.save()
    client = Client()
    client.force_login(user)
    url = reverse("users_mobile_verify")
    response = client.get(url)
    assert response.status_code == 200


# ── AccountAdapter ────────────────────────────────────────────────────────────

@override_settings(DEFAULT_REPLY_TO_EMAIL="reply@example.com")
def test_adapter_render_mail_adds_reply_to():
    from unittest.mock import patch, MagicMock
    adapter = AccountAdapter()
    with patch.object(adapter.__class__.__bases__[0], "render_mail",
                      return_value=MagicMock()) as mock_parent:
        adapter.render_mail("prefix", "to@example.com", {})
        _, kwargs = mock_parent.call_args
        headers = mock_parent.call_args[1].get("headers") or mock_parent.call_args[0][3]
        assert headers.get("Reply-To") == "reply@example.com"


@override_settings(DEFAULT_REPLY_TO_EMAIL=None)
def test_adapter_render_mail_no_reply_to():
    adapter = AccountAdapter()
    with patch.object(adapter.__class__.__bases__[0], "render_mail",
                      return_value=MagicMock()) as mock_parent:
        adapter.render_mail("prefix", "to@example.com", {}, headers=None)
        # Should not set Reply-To when setting is None
        call_args = mock_parent.call_args
        passed_headers = call_args[1].get("headers") if call_args[1] else (
            call_args[0][3] if len(call_args[0]) > 3 else None
        )
        assert passed_headers is None or "Reply-To" not in (passed_headers or {})

