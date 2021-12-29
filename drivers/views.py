from django.shortcuts import render


def create_profile(request):
    context = {}
    return render(request, "drivers/create_profile/step_1_personal_details.html", context)

