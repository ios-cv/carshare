from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def home(request):
    # TODO: Proper logic to decide if the user is incomplete or not needs to go in a decorator.
    if True:
        return redirect("users_incomplete")

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
