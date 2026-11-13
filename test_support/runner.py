from contextlib import ExitStack
from unittest.mock import patch

from django.test.runner import DiscoverRunner


class OfflineDiscoverRunner(DiscoverRunner):
    """Fail unexpected HTTP/SMTP calls while leaving PostgreSQL connections real."""

    def run_tests(self, test_labels, **kwargs):
        with ExitStack() as stack:
            for target in ("requests.sessions.Session.request", "smtplib.SMTP"):
                stack.enter_context(
                    patch(
                        target,
                        side_effect=AssertionError("Unexpected external service call"),
                    )
                )
            return super().run_tests(test_labels, **kwargs)
