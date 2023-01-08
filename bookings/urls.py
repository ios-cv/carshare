from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="bookings_home"),
    path("history/", views.my_bookings, name="bookings_history"),
    path("search/", views.search, name="bookings_search"),
    path("confirm_booking/", views.confirm_booking, name="bookings_confirm"),
    path("cancel/<int:booking>", views.cancel, name="bookings_cancel"),
    path("edit/<int:booking>", views.edit, name="bookings_edit"),
]
