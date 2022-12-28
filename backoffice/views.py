from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from billing.models import (
    get_all_pending_approval as get_all_billing_accounts_pending_approval,
    BillingAccount,
)
from bookings.models import Booking
from drivers.models import (
    get_all_pending_approval as get_all_driver_profiles_pending_approval,
    DriverProfile,
)

from .decorators import require_backoffice_access
from .forms import DriverProfileApprovalForm, DriverProfileReviewForm


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
    return render(request, "backoffice/vehicles.html", context)
