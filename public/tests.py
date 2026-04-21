"""Tests for the public app."""
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_home_unauthenticated_redirects_external():
    client = Client()
    response = client.get(reverse("public_home"))
    assert response.status_code == 302
    assert "ioscv" in response["Location"]


@pytest.mark.django_db
def test_home_authenticated_redirects_to_bookings(make_user):
    user = make_user()
    client = Client()
    client.force_login(user)
    response = client.get(reverse("public_home"))
    assert response.status_code == 302
    assert "bookings" in response["Location"]


@pytest.mark.django_db
def test_privacy_redirects():
    client = Client()
    response = client.get(reverse("public_privacy"))
    assert response.status_code == 302
    assert "privacy" in response["Location"]


@pytest.mark.django_db
def test_terms_redirects():
    client = Client()
    response = client.get(reverse("public_terms"))
    assert response.status_code == 302
    assert "terms" in response["Location"]


@pytest.mark.django_db
def test_help_redirects():
    client = Client()
    response = client.get(reverse("public_help"))
    assert response.status_code == 302
    assert "guide" in response["Location"] or "user" in response["Location"]

