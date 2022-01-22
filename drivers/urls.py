from django.urls import path

from . import views

urlpatterns = [
    path("create", views.create_profile, name="drivers_create_profile"),
    path("create/<int:stage>", views.build_profile, name="drivers_build_profile"),
]
