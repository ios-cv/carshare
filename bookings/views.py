from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from hardware.models import Vehicle
from users.decorators import require_complete_user

from .forms import BookingSearchForm, ConfirmBookingForm
from .models import get_available_vehicles, Booking


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
            context["start"] = form.cleaned_data["start"].isoformat()
            context["end"] = form.cleaned_data["end"].isoformat()
        else:
            context["form"] = form
    else:
        form = BookingSearchForm()
        context["form"] = form

    return render(request, "bookings/new_booking_search.html", context)


@login_required
@require_complete_user
def confirm_booking(request):
    # Must be a POST form.
    if request.method != "POST":
        return redirect("new_booking_search")

    # Also data must be valid as no user entry.
    form = ConfirmBookingForm(request.POST)
    if not form.is_valid():
        print("Invalid form data submitted. This should not happen.")
        # TODO: Proper error logging here.
        return redirect("new_booking_search")

    if form.cleaned_data["confirmed"]:
        Booking.create_booking(
            user=request.user,
            vehicle=Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
            start=form.cleaned_data["start"],
            end=form.cleaned_data["end"],
        )
        return redirect("bookings_history")

    confirm_form = ConfirmBookingForm()
    confirm_form.initial = {
        "start": form.cleaned_data["start"],
        "end": form.cleaned_data["end"],
        "vehicle_id": form.cleaned_data["vehicle_id"],
        "confirmed": True,
    }

    context = {
        "start": form.cleaned_data["start"],
        "end": form.cleaned_data["end"],
        "vehicle": Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
        "form": confirm_form,
    }

    return render(request, "bookings/confirm_booking.html", context)
