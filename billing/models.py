from django.db import models
from django.utils import timezone

from drivers.models import FullDriverProfile
from users.models import User


class BillingAccount(models.Model):
    class Meta:
        db_table = "billing_account"

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
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)

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

    # Extra details for business accounts.
    business_name = models.CharField(max_length=255, null=True, blank=True)
    business_address_line_1 = models.CharField(max_length=100, null=True, blank=True)
    business_address_line_2 = models.CharField(max_length=100, null=True, blank=True)
    business_address_line_3 = models.CharField(max_length=100, null=True, blank=True)
    business_address_line_4 = models.CharField(max_length=100, null=True, blank=True)
    business_postcode = models.CharField(max_length=100, null=True, blank=True)
    business_tax_id = models.CharField(max_length=30, null=True, blank=True)

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

        if self.approved_at is None:
            return False

        return True

    def approve(self):
        self.approved_at = timezone.now()


def get_personal_billing_account_for_user(user):
    return user.owned_billing_accounts.filter(
        account_type=BillingAccount.PERSONAL
    ).first()


def get_all_pending_approval():
    """Returns a QuerySet encapsulating all billing accounts that are pending approval."""
    return BillingAccount.objects.filter(
        stripe_setup_intent_active=True, approved_at=None
    )


class BillingAccountMember(models.Model):
    class Meta:
        db_table = "billing_account_member"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    billing_account = models.ForeignKey(BillingAccount, on_delete=models.CASCADE)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(default=0)

    can_make_bookings = models.BooleanField(default=False)
