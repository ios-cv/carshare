from django.urls import path

from . import views

urlpatterns = [
    path("setup", views.setup, name="billing_setup"),
    path("setup_complete", views.setup_complete, name="billing_setup_complete"),
]
