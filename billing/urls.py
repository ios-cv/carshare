from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(
        r"^setup/(?P<account_type>(business|personal))/$",
        views.setup,
        name="billing_setup",
    ),
    path("setup_complete", views.setup_complete, name="billing_setup_complete"),
]
