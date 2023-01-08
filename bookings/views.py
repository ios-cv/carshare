import logging

from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.datastructures import MultiValueDict

from billing.pricing import calculate_booking_cost
from hardware.models import Vehicle
from users.decorators import require_complete_user, require_user_can_make_bookings

from .forms import (
    BookingSearchForm,
    ConfirmBookingForm,
    BookingDetailsForm,
    EditBookingForm,
)
from .models import (
    get_available_vehicles,
    get_unavailable_vehicles,
    Booking,
    POLICY_CANCELLATION_CUTOFF_HOURS,
)

log = logging.getLogger(__name__)


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
        "cancel_cutoff": POLICY_CANCELLATION_CUTOFF_HOURS,
    }
    return render(request, "bookings/history.html", context)


@login_required
@require_user_can_make_bookings
def search(request):
    context = {
        "menu": "new_booking",
    }
    if request.method == "POST":
        form = BookingSearchForm(request.POST)
        if form.is_valid():
            log.debug("Processing search results")
            vehicles = get_available_vehicles(
                form.cleaned_data["start"],
                form.cleaned_data["end"],
                form.cleaned_data["vehicle_types"],
            )
            context["vehicles"] = vehicles
            context["start"] = form.cleaned_data["start"].isoformat()
            context["end"] = form.cleaned_data["end"].isoformat()

            unavailable_vehicles = get_unavailable_vehicles(
                form.cleaned_data["start"],
                form.cleaned_data["end"],
                form.cleaned_data["vehicle_types"],
            )
            context["unavailable_vehicles"] = unavailable_vehicles

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

    context = {
        "menu": "new_booking",
    }

    if "confirmed" in request.POST:
        form = ConfirmBookingForm(request.user, request.POST)

        if form.is_valid():
            Booking.create_booking(
                user=request.user,
                vehicle=Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
                start=form.cleaned_data["start"],
                end=form.cleaned_data["end"],
                billing_account=form.cleaned_data["billing_account"],
            )

            return redirect("bookings_history")

        context["form"] = form

    else:
        form = BookingDetailsForm(request.POST)
        if not form.is_valid():
            log.warning("Invalid form data submitted. This should not happen.")
            # TODO: Proper error logging here.
            return redirect("bookings_search")

        confirm_form = ConfirmBookingForm(request.user)
        confirm_form.initial = {
            "start": form.cleaned_data["start"],
            "end": form.cleaned_data["end"],
            "vehicle_id": form.cleaned_data["vehicle_id"],
            "confirmed": True,
        }
        confirm_form.set_billing_accounts(form.cleaned_data["end"])

        context["form"] = confirm_form

    context["start"] = form.cleaned_data["start"]
    context["end"] = form.cleaned_data["end"]
    context["vehicle"] = Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"])

    context["cost"] = calculate_booking_cost(
        request.user,
        Vehicle.objects.get(pk=form.cleaned_data["vehicle_id"]),
        form.cleaned_data["start"],
        form.cleaned_data["end"],
    )

    return render(request, "bookings/confirm_booking.html", context)


@login_required
@require_user_can_make_bookings
def cancel(request, booking):
    booking = Booking.objects.get(pk=booking)

    if not booking.can_be_modified_by_user(request.user):
        # TODO: Tell user they don't have permission.
        return redirect("bookings_history")

    # TODO: Record a charge to the user if cancellation is within policy window.

    # Actually cancel the booking.
    booking.state = Booking.STATE_CANCELLED
    booking.save()

    return redirect("bookings_history")


@login_required
@require_user_can_make_bookings
def edit(request, booking):
    booking = Booking.objects.get(pk=booking)

    if not booking.can_be_modified_by_user(request.user):
        # TODO: Tell user they don't have permission.
        return redirect("bookings_history")

    if request.method == "POST":
        form = EditBookingForm(booking, request.POST)

        if form.is_valid():
            # TODO: If edit is within policy window, record a charge to user.

            booking.update_times(form.cleaned_data["start"], form.cleaned_data["end"])
            try:
                booking.save()
                # TODO: Tell the user the booking was changed.
                return redirect("bookings_history")
            except IntegrityError:
                form.add_error(
                    None,
                    "Your booking could not be changed because the vehicle is not available then.",
                )

    else:
        form = EditBookingForm(booking)

    context = {
        "menu": "my_bookings",
        "booking": booking,
        "cancel_cutoff": POLICY_CANCELLATION_CUTOFF_HOURS,
        "form": form,
    }

    return render(request, "bookings/edit.html", context)
