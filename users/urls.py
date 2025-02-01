from allauth.account import views as allauthviews
from django.urls import path, re_path

from . import views

urlpatterns = [
    # AllAuth account-related URL overrides
    path("signup/", views.SignUpView.as_view(), name="account_signup"),
    path("login/", views.LoginView.as_view(), name="account_login"),
    path("logout/", allauthviews.logout, name="account_logout"),
    path(
        "password/reset/",
        views.PasswordResetView.as_view(),
        name="account_reset_password",
    ),
    re_path(
        r"^password/reset/key/(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$",
        views.PasswordResetFromKeyView.as_view(),
        name="account_reset_password_from_key",
    ),
    path(
        "password/reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="account_password_reset_done",
    ),
    path(
        "password/reset/key/done/",
        views.PasswordResetFromKeyDoneView.as_view(),
        name="account_password_reset_key_done",
    ),
    # Email Confirmation
    path(
        "email-verification-sent/",
        views.EmailVerificationSentView.as_view(),
        name="email_verification_sent",
    ),
    path(
        "confirm-email/<str:key>/",
        views.ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    # Users app business logic routes
    path(
        "mobile/add/",
        views.add_mobile,
        name="users_mobile_add",
    ),
    path(
        "mobile/verify/",
        views.verify_mobile,
        name="users_mobile_verify",
    ),
    path(
        "",
        views.profile_my_details,
        name="users_profile_my_details",
    ),
    path("incomplete/", views.incomplete, name="users_incomplete"),
]
