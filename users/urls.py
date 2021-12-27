from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.sign_up, name="signup"),
    path(
        "signup/personal/", views.PersonalSignUpView.as_view(), name="signup_personal"
    ),
    path(
        "signup/business/", views.BusinessSignUpView.as_view(), name="signup_business"
    ),
    path("login/", views.LoginView.as_view(), name="login"),
    path(
        "email-verification-sent/",
        views.EmailVerificationSentView.as_view(),
        name="email_verification_sent",
    ),
    path("confirm-email/<str:key>/", views.ConfirmEmailView.as_view(), name="confirm_email"),
]
