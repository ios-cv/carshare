from django.shortcuts import redirect


def require_incomplete_user(view_func=None):
    """
    Decorator for views that checks that the user has not completed setup
    (mobile, driver profile, billing profile, etc.)
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        # TODO: Add billing profile check if required here once we enable billing.
        if (
            user.has_validated_mobile()
            and user.has_valid_driver_profile()
            and user.has_valid_billing_account()
        ):
            return redirect("bookings_history")
        else:
            return view_func(request, *args, **kwargs)

    return wrapper_func


def require_complete_user(view_func=None):
    """
    Decorator for views that checks that the user has completed the setup process
    (mobile, driver profile, billing profile, etc.) and has an unexpired and validated driver profile.
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        # TODO: Add billing profile check if required here once we enable billing.
        if (
            user.has_validated_mobile()
            and user.has_valid_driver_profile()
            and user.has_valid_billing_account()
        ):
            return view_func(request, *args, **kwargs)
        else:
            return redirect("users_incomplete")

    return wrapper_func
