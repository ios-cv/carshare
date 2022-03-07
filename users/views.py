from django.shortcuts import redirect, render
from allauth.account import views

from .decorators import require_incomplete_user
from .forms import (
    PersonalSignupForm,
    BusinessSignupForm,
    AddMobileForm,
    VerifyMobileForm,
    LoginForm,
)
from .sms import send_sms_verification_code


def sign_up(request):
    context = {}
    return render(request, "users/signup.html", context)


@require_incomplete_user
def incomplete(request):
    context = {
        "user": request.user,
    }
    return render(request, "users/incomplete.html", context)


class PersonalSignUpView(views.SignupView):
    template_name = "users/signup_personal.html"
    form_class = PersonalSignupForm


class BusinessSignUpView(views.SignupView):
    template_name = "users/signup_business.html"
    form_class = BusinessSignupForm


class LoginView(views.LoginView):
    template_name = "users/login.html"
    form_class = LoginForm


class EmailVerificationSentView(views.EmailVerificationSentView):
    template_name = "users/email_verification_sent.html"


class ConfirmEmailView(views.ConfirmEmailView):
    template_name = "users/confirm_email.html"


def add_mobile(request):
    if request.method == "POST":
        form = AddMobileForm(request.POST, instance=request.user)
        if form.is_valid():
            u = form.save()
            send_sms_verification_code(u.mobile_verification_code, u.pending_mobile)
            return redirect("users_mobile_verify")
    else:
        form = AddMobileForm(instance=request.user)

    context = {"form": form}

    return render(request, "users/add_mobile.html", context)


def verify_mobile(request):
    if request.method == "POST":
        form = VerifyMobileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("users_incomplete")
    else:
        form = VerifyMobileForm()

    context = {
        "form": form,
    }
    return render(request, "users/verify_mobile.html", context)
