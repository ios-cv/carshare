from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from drivers.models import FullDriverProfile, ExternalDriverProfile
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
    EXTERNAL = "e"
    DRIVER_PROFILE_TYPE_CHOICES = [
        (FULL, "full"),
        (EXTERNAL, "external"),
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
    business_purchase_order = models.CharField(max_length=100, null=True, blank=True)

    @classmethod
    def by_stripe_customer_id(cls, stripe_customer_id):
        return cls.objects.filter(stripe_customer_id=stripe_customer_id).first()

    @property
    def driver_profile_python_type(self):
        if self.driver_profile_type == BillingAccount.FULL:
            return FullDriverProfile
        if self.driver_profile_type == BillingAccount.EXTERNAL:
            return ExternalDriverProfile
        raise Exception("Not implemented!")

    @property
    def valid(self):
        if self.stripe_customer_id is None:
            return False

        if len(self.stripe_customer_id) == 0:
            return False

        if self.approved_at is None:
            return False

        if self.credit_account:
            return True

        if not self.stripe_setup_intent_active:
            return False

        return True

    @admin.display(
        boolean=True,
        description="Valid",
    )
    def admin__is_valid(self):
        return self.valid

    def approve(self):
        self.approved_at = timezone.now()

    @property
    def approved(self):
        return self.approved_at is not None

    @property
    def complete(self):
        return self.stripe_customer_id and (
            self.stripe_setup_intent_active or self.credit_account
        )

    @admin.display(boolean=True, description="Complete")
    def admin__is_complete(self):
        return self.complete

    @property
    def display_name(self):
        if self.account_type == BillingAccount.PERSONAL:
            return "Personal Billing Account"
        elif self.account_type == BillingAccount.BUSINESS:
            return self.account_name

    @property
    def memberships(self):
        return BillingAccountMember.objects.filter(billing_account=self.id)

    def __str__(self):
        if self.account_type == self.PERSONAL:
            return (
                f"Personal ({self.owner.first_name} {self.owner.last_name}) [{self.id}]"
            )
        else:
            return f"{self.account_name} ({self.owner.first_name} {self.owner.last_name}) [{self.id}]"


def get_personal_billing_account_for_user(user):
    return user.owned_billing_accounts.filter(
        account_type=BillingAccount.PERSONAL
    ).first()


def get_all_pending_approval():
    """Returns a list of all billing accounts that are pending and ready for approval."""
    all_bas = BillingAccount.objects.filter(
        stripe_setup_intent_active=True,
        approved_at=None,
    )

    bas = []
    for ba in all_bas:
        if (
            ba.account_type == BillingAccount.BUSINESS
            or ba.owner.has_valid_driver_profile(ba.driver_profile_python_type)
        ):
            bas.append(ba)

    return bas


class BillingAccountMember(models.Model):
    class Meta:
        db_table = "billing_account_member"
        unique_together = [["billing_account", "user"]]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    billing_account = models.ForeignKey(BillingAccount, on_delete=models.CASCADE)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    can_make_bookings = models.BooleanField(default=False)


class BillingAccountMemberInvitation(models.Model):
    class Meta:
        db_table = "billing_account_member_invitation"

    inviting_user = models.ForeignKey(User, on_delete=models.CASCADE)
    billing_account = models.ForeignKey(
        BillingAccount, on_delete=models.CASCADE, related_name="invitations"
    )

    can_make_bookings = models.BooleanField(default=False)
    email = models.EmailField()
    secret = models.UUIDField()
    created_at = models.DateTimeField()


def get_billing_accounts_suitable_for_booking(user, booking_end):
    """
    This function
    :param user: the user object making the booking
    :param booking_end: localised datetime representing the booking end.
    :return: a **list** containing the Billing Accounts that are valid for the user to be
             allowed to use for this booking.
    """

    # This query gets all valid billing accounts, across ownership and membership,
    # that can be used to make a booking by this user, *without* awareness of authority
    # to drive.
    # TODO: Make this accessible from the User object somehow.
    q = BillingAccount.objects.filter(
        Q(owner=user) | Q(members=user, billingaccountmember__can_make_bookings=True),
        ~Q(approved_at=None),
    )

    return q
