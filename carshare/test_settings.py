"""Isolated defaults for the built-in Django test runner; never deployment settings."""

from .settings import *  # noqa: F403

TEST_RUNNER = "test_support.runner.OfflineDiscoverRunner"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STRIPE_API_KEY = "sk_test_no_network"
STRIPE_PUBLIC_KEY = "pk_test_no_network"
SMS_API_KEY = None
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
LOGGING = {"version": 1, "disable_existing_loggers": False, "root": {"level": "ERROR"}}
