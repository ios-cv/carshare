from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("bookings_home")

    # TODO: Remove temporary redirect here when we have proper home page content.
    return redirect("https://www.ioscv.co.uk/carshare")

    context = {}
    return render(request, "public/home.html", context)


def privacy(request):
    return redirect("https://www.ioscv.co.uk/carshare-privacy-policy")


def terms(request):
    return redirect("https://www.ioscv.co.uk/terms")


def help(request):
    return redirect("https://www.ioscv.co.uk/user-guide")
