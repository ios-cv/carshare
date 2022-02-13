from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from users.decorators import require_complete_user

from .forms import BookingSearchForm
from .models import get_available_vehicles


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


@login_required
@require_complete_user
def new_booking_search(request):
    context = {}
    if request.method == "POST":
        form = BookingSearchForm(request.POST)
        if form.is_valid():
            print("Processing search results")
            vehicles = get_available_vehicles(
                form.cleaned_data["start"], form.cleaned_data["end"]
            )
            context["vehicles"] = vehicles
        else:
            context["form"] = form
    else:
        form = BookingSearchForm()
        context["form"] = form

    return render(request, "bookings/new_booking_search.html", context)
