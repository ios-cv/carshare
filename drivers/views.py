import logging

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .decorators import incomplete_driver_profile_required
from .forms import (
    DriverProfilePart1Form,
    DriverProfilePart2Form,
    DriverProfilePart3Form,
    DriverProfilePart4Form,
    DriverProfilePart5Form,
)
from .models import FullDriverProfile

log = logging.getLogger(__name__)


@login_required
def create_profile(request):
    # See if there's already a valid driver profile.
    valid_driver_profiles = FullDriverProfile.objects.filter(
        user=request.user, expires_at__gte=timezone.now()
    ).order_by("-expires_at")

    if len(valid_driver_profiles) > 0:
        # We have a valid driver profile.
        valid_driver_profile = valid_driver_profiles[0]
        log.debug(
            f"Found a valid driver profile {valid_driver_profile} for user {request.user}"
            f"expiring at {valid_driver_profile.expires_at}"
        )

        if valid_driver_profile.expires_at > timezone.now() + timedelta(days=60):
            # Expires in more than 90 days. The user isn't allowed to access this area.
            # TODO: Maybe explain to them rather than just a blind redirect???
            print(
                "User already has a driver profile that's valid for plenty of time. Redirecting."
            )
            return redirect("bookings_home")
        else:
            log.debug("Driver profile expires soon, so allow user to create a new one.")

    # Find out if there is an incomplete driver profile.
    incomplete_driver_profile = FullDriverProfile.get_incomplete_driver_profile(
        request.user
    )

    if incomplete_driver_profile is None:
        # User doesn't have any incomplete driver profiles. Create a fresh one.
        driver_profile = FullDriverProfile.create(user=request.user)
        driver_profile.save()
        print("User has no valid or invalid driver profiles. Creating a fresh one.")
        stage = 1
    else:
        # User has an incomplete driver profile. Decide which stage to send them to based on approvals
        # received so far.
        stage = 1
        if not incomplete_driver_profile.is_personal_details_approved():
            stage = 1
        elif not incomplete_driver_profile.is_driving_licence_details_approved():
            stage = 2
        elif not incomplete_driver_profile.is_driving_licence_approved():
            stage = 3
        elif not incomplete_driver_profile.is_identity_approved():
            stage = 4
        elif not incomplete_driver_profile.is_driving_record_approved():
            stage = 5

    return redirect("drivers_build_profile", stage=stage)


@login_required
@incomplete_driver_profile_required
def build_profile(request, stage, driver_profile):
    print(driver_profile)

    # If the profile has been submitted for approval, send them to the "approval pending" screen.
    if driver_profile.submitted_at is not None:
        return render(
            request, "drivers/build_profile/step_6_wait_for_approval.html", {
                "hide_driver_profile_warnings": True,
            }
        )

    if stage == 1:
        form_type = DriverProfilePart1Form
        template = "drivers/build_profile/step_1_personal_details.html"
    elif stage == 2:
        form_type = DriverProfilePart2Form
        template = "drivers/build_profile/step_2_driving_licence_details.html"
    elif stage == 3:
        form_type = DriverProfilePart3Form
        template = "drivers/build_profile/step_3_licence_pictures.html"
    elif stage == 4:
        form_type = DriverProfilePart4Form
        template = "drivers/build_profile/step_4_selfie.html"
    elif stage == 5:
        form_type = DriverProfilePart5Form
        template = "drivers/build_profile/step_5_check_code.html"
    else:
        return redirect("drivers_create_profile")

    if request.method == "POST":
        form = form_type(request.POST, request.FILES, instance=driver_profile)
        if form.is_valid():
            form.save()
            return redirect("drivers_build_profile", stage=stage + 1)

    else:
        form = form_type(instance=driver_profile)

    context = {
        "form": form,
        "stage": stage,
        "hide_driver_profile_warnings": True,
    }

    return render(request, template, context)
