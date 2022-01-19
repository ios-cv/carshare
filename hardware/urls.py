from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/unlock", views.unlock, name="box_api_unlock"),
]
