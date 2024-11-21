from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="backoffice_home"),
    path("bookings/", views.bookings, name="backoffice_bookings"),
    path("users/", views.users, name="backoffice_users"),
    path("accounts/", views.accounts, name="backoffice_accounts"),
    path("approvals/", views.approvals, name="backoffice_approvals"),
    path("vehicles/", views.vehicles, name="backoffice_vehicles"),
    path(
        "approvals/driverprofile/<int:id>/",
        views.review_driver_profile,
        name="backoffice_review_driver_profile",
    ),
    path(
        "approvals/driverprofile/<int:id>/final/",
        views.approve_driver_profile,
        name="backoffice_approve_driver_profile",
    ),
    path(
        "approvals/billingaccount/<int:id>/approve/",
        views.approve_billing_account,
        name="backoffice_approve_billing_account",
    ),
    path(
        "approvals/billingaccount/<int:id>/reject/",
        views.reject_billing_account,
        name="backoffice_reject_billing_account",
    ),
]
