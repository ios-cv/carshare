from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/telemetry", views.api_v1_telemetry, name="api_v1_telemetry"),
    path("api/v1/touch", views.api_v1_touch, name="api_v1_touch"),
]
