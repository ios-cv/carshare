from django.test import SimpleTestCase
from django.urls import reverse


class PublicPageTests(SimpleTestCase):
    def test_public_links_redirect_to_expected_destinations(self):
        for name, url in [
            ("public_home", "https://www.ioscv.co.uk/carshare"),
            ("public_terms", "https://www.ioscv.co.uk/terms"),
            ("public_privacy", "https://www.ioscv.co.uk/carshare-privacy-policy"),
            ("public_help", "https://www.ioscv.co.uk/user-guide"),
        ]:
            with self.subTest(name=name):
                self.assertRedirects(
                    self.client.get(reverse(name)), url, fetch_redirect_response=False
                )
