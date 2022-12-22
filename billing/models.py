from django.db import models

from drivers.models import FullDriverProfile
from users.models import User


class BillingAccount(models.Model):
    BUSINESS = "b"
    PERSONAL = "p"
    ACCOUNT_TYPE_CHOICES = [
        (BUSINESS, "business"),
        (PERSONAL, "personal"),
    ]

    FULL = "f"
    COUNCIL = "c"
    DRIVER_PROFILE_TYPE_CHOICES = [
        (FULL, "full"),
        (COUNCIL, "council"),
    ]

    # Owner of the billing account - there must always be exactly 1 owner of any billing account.
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_billing_accounts"
    )

    # Whether this is a personal or business account.
    account_type = models.CharField(
        max_length=1,
        choices=ACCOUNT_TYPE_CHOICES,
    )

    # The name of the account (if it's a business account - not required if personal).
    account_name = models.CharField(max_length=100, null=True, blank=True)

    # The type of driver profile that is required to drive under this billing account.
    driver_profile_type = models.CharField(
        max_length=1,
        choices=DRIVER_PROFILE_TYPE_CHOICES,
    )

    # The customer ID corresponding to this billing account in Stripe.
    stripe_customer_id = models.CharField(max_length=100, null=False)

    # Indicates whether a setup-intent has been put in place for this billing account in stripe.
    stripe_setup_intent_active = models.BooleanField(default=False)

    # Credit account means that invoices will be raised against this customer in Stripe, but
    # there is no payment method on file. This means a payment method does not have to be on file
    # for their account to be treated as valid for billing.
    credit_account = models.BooleanField(default=False)

    # The users who are members of this billing account.
    members = models.ManyToManyField(
        User, through="BillingAccountMember", related_name="billing_accounts"
    )

    # When this billing account was approved.
    approved_at = models.DateTimeField(null=True, default=None, blank=True)

    @classmethod
    def by_stripe_customer_id(cls, stripe_customer_id):
        return cls.objects.filter(stripe_customer_id=stripe_customer_id).first()

    @property
    def driver_profile_python_type(self):
        if self.driver_profile_type == BillingAccount.FULL:
            return FullDriverProfile
        if self.driver_profile_type == BillingAccount.COUNCIL:
            raise Exception("Not implemented!")
        raise Exception("Not implemented!")

    @property
    def valid(self):
        if self.stripe_customer_id is None:
            return False

        if len(self.stripe_customer_id) == 0:
            return False

        if self.credit_account:
            return True

        if not self.stripe_setup_intent_active:
            return False

        return True


def get_personal_billing_account_for_user(user):
    return user.owned_billing_accounts.filter(
        account_type=BillingAccount.PERSONAL
    ).first()


class BillingAccountMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    billing_account = models.ForeignKey(BillingAccount, on_delete=models.CASCADE)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(default=0)

    can_make_bookings = models.BooleanField(default=False)
