from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="backoffice_home"),
    path("bookings", views.bookings, name="backoffice_bookings"),
    path("users", views.users, name="backoffice_users"),
    path("accounts", views.accounts, name="backoffice_accounts"),
    path("approvals", views.approvals, name="backoffice_approvals"),
    path("vehicles", views.vehicles, name="backoffice_vehicles"),
]
