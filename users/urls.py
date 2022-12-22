from django.urls import path

from . import views

urlpatterns = [
    path("incomplete/", views.incomplete, name="users_incomplete"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
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
    path(
        "mobile/add",
        views.add_mobile,
        name="users_mobile_add",
    ),
    path(
        "mobile/verify",
        views.verify_mobile,
        name="users_mobile_verify",
    ),
]
