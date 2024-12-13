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

from django_filters import FilterSet, ModelChoiceFilter

from bookings.models import TsTzRange

from billing.models import (
    get_all_pending_approval as get_all_billing_accounts_pending_approval,
    BillingAccount,
)
from bookings.models import Booking
from drivers.models import (
    get_all_pending_approval as get_all_driver_profiles_pending_approval,
    DriverProfile,
)
from hardware.models import Vehicle, BoxAction
from users.models import User

from .decorators import require_backoffice_access
from .forms import DriverProfileApprovalForm, DriverProfileReviewForm


@require_backoffice_access
def home(request):
    start_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_tomorrow = start_today + timezone.timedelta(days=2)
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
def lock(request, id):
    context = {
        "user": request.user,
    }

    vehicle = Vehicle.objects.get(pk=id)
    context["vehicle"] = vehicle.name
    perform_box_action(
        request=request, vehicle=vehicle, action_to_perform="lock", user=request.user
    )
    return redirect(reverse("backoffice_vehicles"))


@require_backoffice_access
def unlock(request, id):
    context = {
        "user": request.user,
    }

    vehicle = Vehicle.objects.get(pk=id)
    context["vehicle"] = vehicle.name
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
    # message is printed and dispatched regardless of outcome - may be worth exploring options to send different messages
    message = f"{user.username} has {action_to_perform}ed vehicle {vehicle.name} ({vehicle.registration})"
    print(message)
    messages.success(request, message)
    return
