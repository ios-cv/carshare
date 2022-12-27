from django.shortcuts import render

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
    return render(request, "backoffice/approvals.html", context)


@require_backoffice_access
def vehicles(request):
    context = {
        "menu": "vehicles",
        "user": request.user,
    }
    return render(request, "backoffice/vehicles.html", context)
