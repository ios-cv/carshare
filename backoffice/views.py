from django.core.paginator import Paginator
from django.shortcuts import render

from billing.models import (
    get_all_pending_approval as get_all_billing_accounts_pending_approval,
)
from bookings.models import Booking
from drivers.models import (
    get_all_pending_approval as get_all_driver_profiles_pending_approval,
)

from .decorators import require_backoffice_access


@require_backoffice_access
def home(request):
    context = {
        "menu": "dashboard",
        "user": request.user,
    }
    return render(request, "backoffice/home.html", context)


@require_backoffice_access
def bookings(request):
    context = {
        "menu": "bookings",
        "user": request.user,
    }

    bookings = Booking.objects.all().order_by("-reservation_time")
    paginator = Paginator(bookings, 50)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    page_range = paginator.get_elided_page_range(
        number=page_number, on_each_side=1, on_ends=1
    )

    context["page"] = page_obj
    context["page_range"] = page_range

    return render(request, "backoffice/bookings.html", context)


@require_backoffice_access
def users(request):
    context = {
        "menu": "users",
        "user": request.user,
    }
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
def vehicles(request):
    context = {
        "menu": "vehicles",
        "user": request.user,
    }
    return render(request, "backoffice/vehicles.html", context)
