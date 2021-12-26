from django.shortcuts import render
from allauth.account import views


def sign_up(request):
    context = {}
    return render(request, "users/signup.html", context)


class PersonalSignUpView(views.SignupView):
    template_name = "users/signup_personal.html"


class LoginView(views.LoginView):
    template_name = "users/login.html"
