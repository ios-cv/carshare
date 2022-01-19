from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/bonk", views.bonk, name="box_api_bonk"),
]
