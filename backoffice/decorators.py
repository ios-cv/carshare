from django.shortcuts import redirect


def require_backoffice_access(view_func=None):
    """
    Decorator for views that checks that the user has the right
    to access the backoffice area.
    """

    def wrapper_func(request, *args, **kwargs):
        user = request.user

        if user.is_anonymous:
            return redirect("account_login")
        elif user.is_operator:
            return view_func(request, *args, **kwargs)
        else:
            return redirect("bookings_history")

    return wrapper_func
