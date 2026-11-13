from django.urls import re_path
from securemedia.views import media, firmware

# Explicit protected routes avoid relying on URL patterns cached before override_settings.
urlpatterns = [
    re_path(r"^(?P<url>media/hardware/firmware/.*)$", firmware),
    re_path(r"^(?P<url>media/.*)$", media),
]
