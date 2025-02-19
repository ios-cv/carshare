from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import InlineField

from django.conf import settings
from django.contrib.postgres.fields import RangeBoundary
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import ModelChoiceField
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse

import json

from django_filters import FilterSet, ModelChoiceFilter

from bookings.models import TsTzRange, STATE_LATE

from billing.models import (
    get_all_pending_approval as get_all_billing_accounts_pending_approval,
    BillingAccount,
)
from bookings.models import Booking
from drivers.models import (
    get_all_pending_approval as get_all_driver_profiles_pending_approval,
    DriverProfile,
)
from hardware.models import Vehicle, Box, BoxAction, Telemetry
from users.models import User

from .decorators import require_backoffice_access
from .forms import DriverProfileApprovalForm, DriverProfileReviewForm, CloseBookingForm


@require_backoffice_access
def home(request):
    start_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_tomorrow = start_today + timezone.timedelta(days=2)

    drivers_pending = len(get_all_driver_profiles_pending_approval())
    accounts_pending = len(get_all_billing_accounts_pending_approval())

    most_recent_telemetry_query = (
        Telemetry.objects.all()
        .select_related("box", "box__vehicle")
        .order_by("box", "-created_at")
        .distinct("box")
    )

    most_recent_times_telemetry = []
    for tel in most_recent_telemetry_query:
        most_recent_times_telemetry.append(
            {
                "registration": tel.box.vehicle.registration,
                "most_recent": tel.created_at,
            }
        )

    most_recent_soc_query = (
        Telemetry.objects.filter(soc_percent__isnull=False)
        .select_related("box", "box__vehicle")
        .order_by("box", "-created_at")
        .distinct("box")
    )
    most_recent_soc = []
    for tel in most_recent_soc_query:
        most_recent_soc.append(
            {
                "registration": tel.box.vehicle.registration,
                "soc": tel.soc_percent,
                "created_at": tel.created_at,
                "locked": tel.box.locked,
                "vehicle_id": tel.box.vehicle.id,
            }
        )

    for soc_tel in most_recent_soc:
        for tel in most_recent_times_telemetry:
            if tel["registration"] == soc_tel["registration"]:
                soc_tel["most_recent"] = tel["most_recent"]
                break

    most_recent_soc.sort(key=lambda x: x["vehicle_id"], reverse=True)

    context = {
        "menu": "dashboard",
        "user": request.user,
        "bookings": Booking.objects.filter(
            reservation_time__overlap=TsTzRange(
                start_today,
                end_tomorrow,
                RangeBoundary(),
            ),
        ).order_by("-reservation_time"),
        "late_bookings": Booking.objects.filter(
            state=STATE_LATE,
        ).order_by("-reservation_time"),
        "drivers_pending": drivers_pending,
        "accounts_pending": accounts_pending,
        "telemetry": most_recent_soc,
    }
    return render(request, "backoffice/home.html", context)


class VehicleModelChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.registration


class VehicleChoiceFilter(ModelChoiceFilter):
    field_class = VehicleModelChoiceField


class BookingsFilter(FilterSet):
    vehicle = VehicleChoiceFilter(
        queryset=Vehicle.objects.all().order_by("registration"),
        empty_label="All vehicles",
    )

    class Meta:
        model = Booking
        fields = ["vehicle"]

    def get_form_class(self):
        form = super().get_form_class()
        form.helper = FormHelper()
        form.helper.disable_csrf = True
        form.helper.layout = Layout(
            InlineField("vehicle"),
        )

        return form


@require_backoffice_access
def bookings(request):
    context = {
        "menu": "bookings",
        "user": request.user,
    }

    filter = BookingsFilter(
        request.GET, queryset=Booking.objects.all().order_by("-reservation_time")
    )
    bookings = filter.qs
    paginator = Paginator(bookings, 50)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_number, on_each_side=1, on_ends=1
    )

    context["page"] = page_obj
    context["page_range"] = page_range
    context["filter"] = filter

    # Hack for pagination & filtering. Should really use a templatetag to generate URLs.
    _request_copy = request.GET.copy()
    parameters = _request_copy.pop("page", True) and _request_copy.urlencode()
    context["parameters"] = parameters

    return render(request, "backoffice/bookings.html", context)


@require_backoffice_access
def users(request):
    context = {
        "menu": "users",
        "user": request.user,
    }

    query = request.GET.get("q")

    if query:
        context["q"] = query

    if query:
        users_partial = User.objects.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(mobile__icontains=query)
        ).distinct()
    else:
        users_partial = User.objects.all()

    users = users_partial.order_by("first_name", "last_name")

    paginator = Paginator(users, 100)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_number, on_each_side=1, on_ends=1
    )

    context["page"] = page_obj
    context["page_range"] = page_range

    return render(request, "backoffice/users.html", context)


@require_backoffice_access
def accounts(request):
    context = {
        "menu": "accounts",
        "user": request.user,
    }
    return render(request, "backoffice/accounts.html", context)


@require_backoffice_access
def approvals(request):
    context = {
        "menu": "approvals",
        "user": request.user,
    }

    billing_accounts = get_all_billing_accounts_pending_approval()
    driver_profiles = get_all_driver_profiles_pending_approval()

    context["billing_accounts"] = billing_accounts
    context["driver_profiles"] = driver_profiles

    return render(request, "backoffice/approvals.html", context)


@require_backoffice_access
def review_driver_profile(request, id):
    context = {
        "menu": "approvals",
        "user": request.user,
    }

    # TODO: Handle different types of Driver Profile here.
    driver_profile = DriverProfile.objects.get(pk=id)

    context["driver_profile"] = driver_profile

    if request.method == "POST":
        form = DriverProfileReviewForm(
            request.POST, request.FILES, instance=driver_profile
        )
        if form.is_valid():
            if form.instance.is_anything_rejected():
                form.instance.submitted_at = None
            form.save()

            context["updated"] = True

    else:
        form = DriverProfileReviewForm(instance=driver_profile)

    # If form has been returned to user for extra information, redirect to
    # the waiting approvals list page.
    if form.instance.submitted_at is None:
        return redirect("backoffice_approvals")

    # If the form is fully approved, redirect to the final-approval page.
    print(form.instance.can_profile_be_approved())
    if form.instance.can_profile_be_approved():
        return redirect("backoffice_approve_driver_profile", id=driver_profile.id)

    context["form"] = form

    return render(request, "backoffice/review_driver_profile.html", context)


@require_backoffice_access
def approve_driver_profile(request, id):
    context = {
        "menu": "approvals",
        "user": request.user,
    }

    # TODO: Handle different types of Driver Profile here.
    driver_profile = DriverProfile.objects.get(pk=id)

    if request.method == "POST":
        form = DriverProfileApprovalForm(driver_profile, request.POST)
        if form.is_valid():
            form.save(request.user)
            # TODO: Add a notification to say this is done.
    else:
        form = DriverProfileApprovalForm(driver_profile)

    if driver_profile.approved_at is not None:
        return redirect("backoffice_approvals")

    context["form"] = form

    return render(request, "backoffice/approve_driver_profile.html", context)


@require_backoffice_access
def approve_billing_account(request, id):
    # FIXME: Validate whether this action should be allowed here before performing it.
    ba = BillingAccount.objects.get(pk=id)
    ba.approve()
    ba.save()

    if ba.owner.has_valid_driver_profile(profile_type=ba.driver_profile_python_type):
        email_ctx = {
            "user": ba.owner,
            "billing_account": ba,
            "link": request.build_absolute_uri(reverse("bookings_search")),
        }

        email = EmailMessage(
            "Your GO-EV account has been approved",
            render_to_string(
                "backoffice/emails/billing_account_approved.txt", email_ctx
            ),
            None,
            [ba.owner.email],
            reply_to=(
                None
                if settings.DEFAULT_REPLY_TO_EMAIL is None
                else [settings.DEFAULT_REPLY_TO_EMAIL]
            ),
        )
        email.send(fail_silently=False)

    # TODO: Notification before redirecting reporting on the success/failure of this action.
    return redirect("backoffice_approvals")


@require_backoffice_access
def reject_billing_account(request, id):
    # FIXME: Validate whether this action should be allowed here before performing it.
    ba = BillingAccount.objects.get(pk=id)
    ba.delete()
    # TODO: Delete the corresponding billing account in Stripe too.
    # TODO: Notification before redirecting reporting on the success/failure of this action.
    return redirect("backoffice_approvals")


@require_backoffice_access
def vehicles(request):
    context = {
        "menu": "vehicles",
        "user": request.user,
    }

    vehicles = Vehicle.objects.all().order_by("-id")
    paginator = Paginator(vehicles, 50)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_number, on_each_side=1, on_ends=1
    )

    context["page"] = page_obj
    context["page_range"] = page_range

    return render(request, "backoffice/vehicles.html", context)


@require_backoffice_access
def close_booking(request, booking_id):
    booking = Booking.objects.get(pk=booking_id)

    form = CloseBookingForm(request.GET or None)
    if form.is_valid():
        should_lock = form.cleaned_data.get("should_lock")
        return_url = form.cleaned_data.get("return_url")
    else:
        should_lock = False
        return_url = reverse("backoffice_home")

    # Don't allow closing the booking if it hasn't started yet.
    if not booking.reservation_started():
        message = f"Failed to close booking #{booking_id} as it hasn't started yet."
        messages.error(request, message)
        return redirect(return_url)

    # FIXME: potential race condition as booking state could have been changed elsewhere
    if not booking.in_closeable_state():
        message = f"Failed to close booking #{booking_id} as it is in an inappropriate state: {booking.get_state_display()}."
        messages.error(request, message)
        return redirect(return_url)

    booking.state = Booking.STATE_INACTIVE
    booking.save()

    box = Box.objects.get(pk=booking.vehicle.box.id)
    # FIXME: May also be a race condition
    if box.current_booking == booking:
        box.current_booking = None
        box.unlocked_by = None
        box.save()

    message = f"Booking #{booking_id} closed."
    messages.success(request, message)

    if should_lock:
        time_to_expire = timezone.now() + timezone.timedelta(minutes=10)
        action = BoxAction(
            action="lock",
            created_at=timezone.now(),
            expires_at=time_to_expire,
            box=box,
            user_id=request.user.id,
        )
        action.save()

        box = Box.objects.get(pk=booking.vehicle.box.id)
        box.locked = True
        box.save()

        message = f"Lock action sent to vehicle {box.vehicle.registration}."
        messages.success(request, message)

    return redirect(return_url)


@require_backoffice_access
def lock(request, id):
    vehicle = Vehicle.objects.get(pk=id)
    perform_box_action(
        request=request, vehicle=vehicle, action_to_perform="lock", user=request.user
    )
    return redirect(reverse("backoffice_vehicles"))


@require_backoffice_access
def unlock(request, id):
    vehicle = Vehicle.objects.get(pk=id)
    perform_box_action(
        request=request, vehicle=vehicle, action_to_perform="unlock", user=request.user
    )
    return redirect(reverse("backoffice_vehicles"))


def perform_box_action(request, vehicle, action_to_perform, user):
    box_id = vehicle.box
    time_to_expire = timezone.now() + timezone.timedelta(minutes=10)
    action = BoxAction(
        action=action_to_perform,
        created_at=timezone.now(),
        expires_at=time_to_expire,
        box=box_id,
        user_id=user.id,
    )
    action.save()
    vehicle.box.locked = True if action_to_perform == "lock" else False
    vehicle.box.save()
    # FIXME: message is dispatched regardless of outcome - may be worth exploring options to send different messages
    message = f"{user.username} has {action_to_perform}ed vehicle {vehicle.name} ({vehicle.registration})"
    messages.success(request, message)

@require_backoffice_access
def vehicle_details(request, vehicle_id):
    vehicle=Vehicle.objects.get(pk=vehicle_id)
    next_booking=Booking.objects.filter(vehicle=vehicle,reservation_time__startswith__gt=timezone.now()).order_by("reservation_time").first()
    current_booking=Booking.objects.filter(vehicle=vehicle,reservation_time__startswith__lt=timezone.now(),reservation_time__endswith__gt=timezone.now()).order_by("reservation_time").first()
    last_booking=Booking.objects.filter(vehicle=vehicle,reservation_time__endswith__lt=timezone.now()).order_by("-reservation_time").first()
    telemetry=Telemetry.objects.filter(box=vehicle.box).order_by("-created_at")[:5040]

    most_recent={
        "battery":None,
        "soc":None,
        "free_heap":None,
        "uptime":None,
        "doors_locked":None,
        "miles":None,
    }
    for t in telemetry:
        if most_recent["battery"] is None and t.aux_battery_voltage is not None:
            most_recent["battery"]={
                "value":t.aux_battery_voltage,
                "age":timezone.now()-t.created_at,
            }
        if most_recent["soc"] is None and t.soc_percent is not None:
            most_recent["soc"]={
                "value":t.soc_percent,
                "age":timezone.now()-t.created_at
            }
        if most_recent["free_heap"] is None and t.box_free_heap_bytes is not None:
            most_recent["free_heap"]={
                "value":t.free_heap_bytes_to_str(),
                "age":timezone.now()-t.created_at
            }
        if most_recent["uptime"] is None and t.box_uptime_s is not None:
            most_recent["uptime"]={
                "value":t.uptime_to_str(),
                "age":timezone.now()-t.created_at
            }
        if most_recent["doors_locked"] is None and t.doors_locked is not None:
            most_recent["doors_locked"]={
                "value":t.doors_locked,
                "age":timezone.now()-t.created_at
            }
        if most_recent["miles"] is None and t.odometer_miles is not None:
            most_recent["miles"]={
                "value":t.odometer_miles,
                "age":timezone.now()-t.created_at
            }
        #Stop looking through telemetry if all most_recent values found
        if all(value is not None for value in most_recent.values()):
            break
    
    for key in most_recent:
        if most_recent[key] is not None:
            most_recent[key]["age"]=breakdown_timedelta(most_recent[key]["age"])
            
    if most_recent["soc"] is not None:
        most_recent["soc_dial"]=251.2 * (1-t.soc_percent/100)
    else:
        most_recent["soc_dial"]=0


    paginator = Paginator(telemetry, 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_number, on_each_side=1, on_ends=1
    )

    context={
        "vehicle":vehicle,
        "telemetry":telemetry,
        "most_recent":most_recent,
        "page":page_obj,
        "page_range":page_range,
        "bookings":[last_booking,current_booking,next_booking],
    }
    return render(request,"backoffice/vehicles/details.html",context)

def breakdown_timedelta(timedelta):
    seconds_in_an_hour=60*60
    seconds_in_a_day=24*seconds_in_an_hour
    seconds_in_a_month=30*seconds_in_a_day
    seconds_in_a_year=365*seconds_in_a_day

    all_seconds=timedelta.days*seconds_in_a_day+timedelta.seconds
    years, seconds_remaining=divmod(all_seconds,seconds_in_a_year)
    months, seconds_remaining=divmod(seconds_remaining,seconds_in_a_month)
    days, seconds_remaining=divmod(seconds_remaining,seconds_in_a_day)
    hours, seconds_remaining=divmod(seconds_remaining,seconds_in_an_hour)
    minutes, seconds_remaining=divmod(seconds_remaining,60)
    seconds=int(seconds_remaining)
    if years>0:
        years_str=f"{years} years, "
    else:
        years_str=""
    if months>0:
        months_str=f"{months} months, "
    else:
        months_str=""
    if days>0:
        days_str=f"{days} days, "
    else:
        days_str=""
    if hours>0:
        hours_str=f"{hours} hours, "
    else:
        hours_str=""
    if minutes>0:
        minutes_str=f"{minutes} minutes, "
    else:
        minutes_str=""
    if seconds>0:
        seconds_str=f"and {seconds} seconds"
    else:
        seconds_str=""
    
    return f"{years_str}{months_str}{days_str}{hours_str}{minutes_str}{seconds_str}"

@require_backoffice_access
def get_telemetry(request):
    vehicle_id=None
    if request.body:
        data=json.loads(request.body)
        vehicle_id=int(data.get("vehicle_id",None))
    if vehicle_id is not None:
        vehicle=Vehicle.objects.get(pk=vehicle_id)
    else:
        return JsonResponse("Invalid vehicle id",safe=False)
    
    telemetry=Telemetry.objects.filter(box=vehicle.box).order_by("-created_at")[:5040]
    telemetry=telemetry.values_list(
        "soc_percent",
        "odometer_miles",
        "doors_locked",
        "aux_battery_voltage",
        "box_uptime_s",
        "box_free_heap_bytes",
        "created_at"
        )
    
    telemetry_json=[
        dict({
            "soc": soc_percent,
            "odometer": odometer_miles,
            "doors_locked": doors_locked,
            "battery": aux_battery_voltage,
            "uptime": box_uptime_s,
            "free_heap": box_free_heap_bytes,
            "created_at": created_at.timestamp()})
            for soc_percent, odometer_miles, doors_locked, aux_battery_voltage, box_uptime_s, box_free_heap_bytes, created_at in telemetry
    ]

    return JsonResponse(telemetry_json, safe=False)
