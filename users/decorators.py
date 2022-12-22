from django.shortcuts import redirect


def require_incomplete_user(view_func=None):
    """
    Decorator for views that checks that the user has not completed setup
    (mobile, driver profile, billing profile, etc.)
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.can_drive() or user.can_make_bookings():
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

        if user.can_drive() or user.can_make_bookings():
            return view_func(request, *args, **kwargs)
        else:
            return redirect("users_incomplete")

    return wrapper_func


def require_user_can_make_bookings(view_func=None):
    """
    Decorator for views that checks that the user has at least one account affiliation
    through which they are allowed to make bookings.
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.can_make_bookings():
            return view_func(request, *args, **kwargs)
        else:
            # TODO: Redirect to the profile main page instead to avoid redirect loop.
            return redirect("users_incomplete")

    return wrapper_func
