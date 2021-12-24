from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect('bookings_home')

    context = {}
    return render(request, "public/home.html", context)
