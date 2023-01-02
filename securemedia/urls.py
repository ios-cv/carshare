from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path

from . import views

urlpatterns = []

if settings.PROTECT_MEDIA:
    urlpatterns.append(re_path(rf"^(?P<url>{settings.MEDIA_URL[1:]}.*)/$", views.media))
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
