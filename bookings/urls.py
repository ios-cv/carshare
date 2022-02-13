from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="bookings_home"),
    path("history/", views.my_bookings, name="bookings_history"),
    path("create/", views.new_booking, name="bookings_create"),
    path("new_booking_search/", views.new_booking_search, name="new_booking_search"),
]
