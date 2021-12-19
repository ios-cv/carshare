from django.http import HttpResponse
from django.shortcuts import render


def sign_up(request):
    context = {}
    return render(request, "users/signup.html", context)
