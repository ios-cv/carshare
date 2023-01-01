"""carshare URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("users/", include("users.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("bookings/", include("bookings.urls")),
    path("drivers/", include("drivers.urls")),
    path("hardware/", include("hardware.urls")),
    path("billing/", include("billing.urls")),
    path("backoffice/", include("backoffice.urls")),
    path("", include("public.urls")),
]

if settings.PROTECT_MEDIA:
    urlpatterns.append(re_path(rf"^(?P<url>{settings.MEDIA_URL[1:]}.*)/$", views.media))
else:
    static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
