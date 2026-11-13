from django.test import override_settings
from test_support import factories as f
from test_support.cases import FrozenTestCase


@override_settings(
    ROOT_URLCONF="test_support.media_urls",
    PROTECT_MEDIA=True,
    MEDIA_URL="/media/",
    MEDIA_PROTECTED_URL="internal/",
)
class ProtectedMediaTests(FrozenTestCase):
    def setUp(self):
        super().setUp()
        self.owner = f.user()
        self.path = "drivers/profiles/licence_front/test.jpg"
        f.profile(self.owner, licence_front=self.path)
        self.url = "/media/" + self.path

    def test_owner_receives_internal_redirect(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Accel-Redirect"], "/internal/" + self.path)
        self.assertEqual(response.content, b"")

    def test_unrelated_and_anonymous_users_cannot_read_document(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(f.user())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("X-Accel-Redirect", response)

    def test_privileged_media_roles(self):
        for flags in [
            {"is_operator": True},
            {"is_staff": True},
            {"is_superuser": True},
        ]:
            with self.subTest(flags=flags):
                self.client.force_login(f.user(**flags))
                self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_firmware_route_requires_device_credentials(self):
        self.client.force_login(f.user(is_operator=True))
        self.assertEqual(
            self.client.get("/media/hardware/firmware/test.bin").status_code, 401
        )
