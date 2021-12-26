from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    context = {}
    return render(request, "bookings/home.html", context)


@login_required
def my_bookings(request):
    context = {}
    return render(request, "bookings/history.html", context)


@login_required
def new_booking(request):
    context = {}
    return render(request, "bookings/create.html", context)
