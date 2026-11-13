from unittest.mock import patch
from django.test import TestCase
from .factories import NOW


class FrozenTestCase(TestCase):
    def setUp(self):
        super().setUp()
        clock = patch("django.utils.timezone.now", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)
