"""Tests for the securemedia app."""
import uuid

import pytest
from django.conf import settings
from django.test import Client, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser


# ── nginx_redirect ────────────────────────────────────────────────────────────

@override_settings(MEDIA_PROTECTED_URL="protected/", MEDIA_URL="/media/")
def test_nginx_redirect_headers():
    from securemedia.views import nginx_redirect
    response = nginx_redirect("drivers/profiles/licence_front/test.jpg")
    assert response["X-Accel-Redirect"] == "/protected/drivers/profiles/licence_front/test.jpg"
    assert response["Content-Type"] == ""


# ── media view ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(PROTECT_MEDIA=True, MEDIA_URL="/media/",
                   MEDIA_PROTECTED_URL="protected/")
def test_media_wrong_url_prefix_raises_404(make_user):
    from django.test import RequestFactory
    from securemedia.views import media
    from django.http import Http404
    factory = RequestFactory()
    user = make_user()
    user.is_operator = False
    user.is_staff = False
    user.is_superuser = False
    request = factory.get("/bad/path.jpg")
    request.user = user
    with pytest.raises(Http404):
        media(request, "bad/path.jpg")


@pytest.mark.django_db
@override_settings(PROTECT_MEDIA=True, MEDIA_URL="/media/",
                   MEDIA_PROTECTED_URL="protected/")
def test_media_operator_can_see_all(make_user):
    from django.test import RequestFactory
    from securemedia.views import media
    factory = RequestFactory()
    user = make_user(is_operator=True)
    request = factory.get("/media/drivers/profiles/licence_front/test.jpg")
    request.user = user
    response = media(request, "media/drivers/profiles/licence_front/test.jpg")
    assert response.status_code == 200
    assert "X-Accel-Redirect" in response


@pytest.mark.django_db
@override_settings(PROTECT_MEDIA=True, MEDIA_URL="/media/",
                   MEDIA_PROTECTED_URL="protected/")
def test_media_hardware_public(make_user):
    from django.test import RequestFactory
    from securemedia.views import media
    factory = RequestFactory()
    user = make_user()
    user.is_staff = False
    user.is_superuser = False
    request = factory.get("/media/hardware/firmware/test.bin")
    request.user = user
    response = media(request, "media/hardware/firmware/test.bin")
    assert response.status_code == 200
    assert "X-Accel-Redirect" in response


@pytest.mark.django_db
@override_settings(PROTECT_MEDIA=True, MEDIA_URL="/media/",
                   MEDIA_PROTECTED_URL="protected/")
def test_media_unknown_path_raises_404(make_user):
    from django.test import RequestFactory
    from securemedia.views import media
    from django.http import Http404
    factory = RequestFactory()
    user = make_user()
    user.is_staff = False
    user.is_superuser = False
    request = factory.get("/media/unknown/path/file.txt")
    request.user = user
    with pytest.raises(Http404):
        media(request, "media/unknown/path/file.txt")

