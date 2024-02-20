from django.shortcuts import redirect


def require_incomplete_user(view_func=None):
    """
    Decorator for views that checks that the user has not completed setup
    (mobile, driver profile, billing profile, etc.)
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.can_drive() and user.has_access_to_valid_billing_account():
            return redirect("bookings_history")
        else:
            return view_func(request, *args, **kwargs)

    return wrapper_func


def require_user_can_make_bookings(view_func=None):
    """
    Decorator for views that checks that the user has at least one account affiliation
    through which they are allowed to make bookings.

    This decorator should only be used to gate whether the user is allowed to interact
    with the create-update-delete cycle of bookings in the system. It doesn't provide
    any guarantee as to whether the user is actually allowed to drive any given
    booking (or any bookings at all).
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.can_make_bookings():
            return view_func(request, *args, **kwargs)
        else:
            # TODO: Redirect to the profile main page instead to avoid redirect loop.
            return redirect("users_incomplete")

    return wrapper_func


def require_user_can_access_bookings(view_func=None):
    """
    Decorator for views that checks that the user has at least one account affiliation
    through which they are allowed to access bookings.
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.can_access_bookings():
            return view_func(request, *args, **kwargs)
        else:
            # TODO: Redirect to the profile main page instead to avoid redirect loop.
            return redirect("users_incomplete")

    return wrapper_func
