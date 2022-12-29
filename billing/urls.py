from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(
        r"^create_account/(?P<billing_account_type>(business|personal))/$",
        views.create_billing_account,
        name="billing_create_account",
    ),
    path(
        "set_payment/<int:billing_account>",
        views.set_payment,
        name="billing_set_payment",
    ),
    path("setup_complete", views.setup_complete, name="billing_setup_complete"),
]
