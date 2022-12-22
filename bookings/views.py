from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict

from billing.pricing import calculate_booking_cost
from hardware.models import Vehicle
from users.decorators import require_complete_user, require_user_can_make_bookings

from .forms import BookingSearchForm, ConfirmBookingForm
from .models import get_available_vehicles, Booking


@login_required
def home(request):
    return redirect("bookings_history")


@login_required
@require_complete_user
def my_bookings(request):
    context = {
        "bookings": Booking.objects.filter(user_id=request.user.id).order_by(
            "-reservation_time"
        ),
        "menu": "my_bookings",
    }
    return render(request, "bookings/history.html", context)


@login_required
@require_user_can_make_bookings
def new_booking(request):
    context = {
        "menu": "new_booking",
    }
    return render(request, "bookings/create.html", context)


@login_required
@require_user_can_make_bookings
def search(request):
    context = {
        "menu": "new_booking",
    }
    if request.method == "POST":
        form = BookingSearchForm(request.POST)
        if form.is_valid():
            print("Processing search results")
            # TODO: Take into account chosen vehicle types.
            vehicles = get_available_vehicles(
                form.cleaned_data["start"], form.cleaned_data["end"]
            )
            context["vehicles"] = vehicles
            context["start"] = form.cleaned_data["start"].isoformat()
            context["end"] = form.cleaned_data["end"].isoformat()

            context["search_terms"] = {
                "start": form.cleaned_data["start"],
                "end": form.cleaned_data["end"],
                "vehicle_types": ", ".join(
                    [vt.name for vt in form.cleaned_data["vehicle_types"]]
                ),
            }

            # This is the form data for going back to edit the search terms.
            context["search_form_data"] = MultiValueDict()
            context["search_form_data"].appendlist("start_0", request.POST["start_0"])
            context["search_form_data"].appendlist("start_1", request.POST["start_1"])
            context["search_form_data"].appendlist("end_0", request.POST["end_0"])
            context["search_form_data"].appendlist("end_1", request.POST["end_1"])
            context["search_form_data"].appendlist("modify", "true")
            for vt in request.POST.getlist("vehicle_types"):
                context["search_form_data"].appendlist("vehicle_types", vt)

        else:
            context["form"] = form
    else:
        if "modify" in request.GET:
            form = BookingSearchForm(request.GET)
        else:
            form = BookingSearchForm()

        context["form"] = form

    return render(request, "bookings/search.html", context)


@login_required
@require_user_can_make_bookings
def confirm_booking(request):
    # Must be a POST form.
    if request.method != "POST":
        return redirect("bookings_search")

    # Also data must be valid as no user entry.
    form = ConfirmBookingForm(request.POST)
    if not form.is_valid():
        print("Invalid form data submitted. This should not happen.")
        # TODO: Proper error logging here.
        return redirect("bookings_search")

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
        "menu": "new_booking",
        "start": form.cleaned_data["start"],
        "end": form.cleaned_data["end"],
        "vehicle": Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
        "form": confirm_form,
        "cost": calculate_booking_cost(
            request.user,
            Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
            form.cleaned_data["start"],
            form.cleaned_data["end"],
        ),
    }

    return render(request, "bookings/confirm_booking.html", context)
