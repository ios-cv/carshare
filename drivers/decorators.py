from django.shortcuts import redirect

from .models import FullDriverProfile


def incomplete_driver_profile_required(view_func=None):
    """
    Decorator for views that checks that the user has an incomplete driver profile and redirects
    them to the view that creates driver profiles if not.
    """

    def wrapper_func(request, *args, **kwargs):
        incomplete_driver_profile = FullDriverProfile.get_incomplete_driver_profile(
            request.user
        )
        if incomplete_driver_profile is None:
            return redirect("drivers_create_profile")
        else:
            return view_func(
                request, *args, driver_profile=incomplete_driver_profile, **kwargs
            )

    return wrapper_func
