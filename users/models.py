import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone


class User(AbstractUser):
    mobile = models.CharField(max_length=32, null=True)
    pending_mobile = models.CharField(max_length=32, null=True)
    mobile_verification_code = models.CharField(max_length=6, null=True)
    billing_account = models.ForeignKey(
        "BillingAccount", null=True, on_delete=models.SET_NULL
    )
    is_operator = models.BooleanField(default=False)

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

    def has_pending_driver_profile(self):
        """Returns True if the user has a submitted driver profile pending review, otherwise False."""
        for dp in self.driver_profiles.filter(
            ~Q(approved_to_drive=True),
            submitted_at__isnull=False,
        ):
            return True

        return False

    def has_valid_billing_account(self):
        """Returns True if the user is associated with a valid billing account, otherwise False."""

        # FIXME: This may need to get a bit more complicated as we don't currently track whether
        #        there is a working card or other type of payment authorisation on the account.
        if self.billing_account is None:
            return False

        if self.billing_account.stripe_customer_id is None:
            return False

        if len(self.billing_account.stripe_customer_id) == 0:
            return False

        if self.billing_account.credit_account:
            return True

        if not self.billing_account.stripe_setup_intent_active:
            return False

        return True


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

    # FIXME: Change stripe id to mandatory field before release.
    stripe_customer_id = models.CharField(max_length=100, null=True)

    # Indicates whether a setup-intent has been put in place for this billing account in stripe.
    stripe_setup_intent_active = models.BooleanField(default=False)

    # Credit account means that invoices will be raised against this customer in Stripe, but
    # there is no payment method on file. This means a payment method does not have to be on file
    # for their account to be treated as valid for billing.
    credit_account = models.BooleanField(default=False)
