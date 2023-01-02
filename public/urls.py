from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="public_home"),
    path("terms", views.terms, name="public_terms"),
    path("privacy", views.privacy, name="public_privacy"),
    path("help", views.privacy, name="public_help"),
]
