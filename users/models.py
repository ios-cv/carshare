import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    mobile = models.CharField(max_length=32, null=True)
    pending_mobile = models.CharField(max_length=32, null=True)
    mobile_verification_code = models.CharField(max_length=6, null=True)
    billing_account = models.ForeignKey(
        "BillingAccount", null=True, on_delete=models.SET_NULL
    )

    @staticmethod
    def generate_verification_code():
        digits = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]
        return "".join([random.choice(digits) for i in range(0, 6)])

    def has_validated_mobile(self):
        """Returns True if the user has complete validation of their mobile number, otherwise False."""
        return self.mobile is not None

    def mobile_validation_pending(self):
        """
        Returns True if the user has requested a mobile validation token but validation is not yet complete.

        Note: if the user is  changing their mobile number, this will return true even though `has_validated_mobile`
        will also return True, as they currently have an (old) validated mobile number, but another (new) number is
        pending validation.
        """
        return self.pending_mobile is not None

    def has_valid_driver_profile(self):
        """Returns True if the user has a currently valid driver profile, otherwise False."""
        for dp in self.driver_profiles.filter(
            approved_to_drive=True, expires_at__gt=timezone.now()
        ):
            print(dp.expires_at)
            print(dp)
            return True

        return False


class BillingAccount(models.Model):
    BUSINESS = "b"
    PERSONAL = "p"
    ACCOUNT_TYPE_CHOICES = [
        (BUSINESS, "Business"),
        (PERSONAL, "personal"),
    ]

    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    type = models.CharField(
        max_length=1,
        choices=ACCOUNT_TYPE_CHOICES,
    )
    account_name = models.CharField(max_length=100, null=True)

    # FIXME: Change stripe id to manadatory field before release.
    stripe_customer_id = models.CharField(max_length=100, null=True)
