import logging
import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone

log = logging.getLogger(__name__)


class User(AbstractUser):
    mobile = models.CharField(max_length=32, null=True, blank=True)
    pending_mobile = models.CharField(max_length=32, null=True, blank=True)
    mobile_verification_code = models.CharField(max_length=6, null=True, blank=True)
    is_operator = models.BooleanField(default=False)

    class Meta:
        db_table = "user"

    def __str__(self):
        return f"{self.first_name} {self.last_name} [{self.id}]"

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

    def has_valid_driver_profile(self, profile_type=None, at=None):
        """
        Find out if a user has a valid driver profile in place, with the optional
        profile_type and "at" time constraints.
        """
        log.debug(
            f"has_valid_driver_profile() called for user: {self.id} with profile_type={profile_type} and at={at}."
        )

        if at is None:
            at = timezone.now()

        base = self.driver_profiles
        if profile_type is not None:
            base = self.driver_profiles.instance_of(profile_type)

        for dp in base.filter(~Q(approved_at=None), expires_at__gt=at):
            log.debug(
                f"User {self.id} has valid driver profile {dp} which expires at {dp.expires_at}"
            )
            return True

        log.debug(
            f"User {self.id} has no valid driver profiles matching the specified criteria"
        )
        return False

    def can_drive(self):
        """
        This method indicates whether the user has completed the minimum
        necessary steps to be able to drive vehicles in any capacity.

        :return: True if the user can drive, otherwise False.
        """

        # First, the user must have their mobile phone number validated.
        log.debug(f"Checking if user: {self.id} is allowed to drive.")
        if not self.has_validated_mobile():
            log.debug(f"User: {self.id} does not have a validated mobile phone number.")
            return False

        # Next we must check if the user has any valid driver profile in place.
        for dp in self.driver_profiles.filter(
            approved_to_drive=True, expires_at__gt=timezone.now()
        ):
            log.debug(
                f"Found a valid driver profile: {dp.id} for user: {self.id}. User can drive."
            )
            return True

        log.debug(
            f"Failed to find a valid driver profile for user: {self.id}. User cannot drive."
        )
        return False

    def is_own_personal_account_validated(self):
        """
        This method indicates whether the user has got a personal driving account set
        up and approved and valid to drive.

        :return: True if the user has a valid personal driving account, otherwise False
        """
        log.debug(f"Checking if own personal account is validated for user: {self.id}")

        # First check for a personal billing account that's been approved.
        personal_billing_account = self.owned_billing_accounts.filter(
            ~Q(approved_at=None), account_type="p"
        ).first()

        if personal_billing_account is None:
            log.debug(f"No own personal billing account found for user: {self.id}")
            return False

        log.debug(
            f"Own personal billing account {personal_billing_account.id} found for user: {self.id}"
        )

        # Then check for an approved driver profile of the appropriate type.
        driver_profile_type = personal_billing_account.driver_profile_python_type
        driver_profile = (
            self.driver_profiles.instance_of(driver_profile_type)
            .filter(
                approved_to_drive=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )

        if driver_profile is None:
            log.debug(
                f"No valid driver profile found for user: {self.id} "
                f"that is compatible with own billing account: {personal_billing_account.id}"
            )
            return False

        # If we made it this far then we're OK.
        log.debug(f"Own personal account for user: {self.id} is fully validated")
        return True

    def is_own_personal_account_pending_validation(self):
        log.debug(f"Checking if own personal account is pending for user: {self.id}")

        # First check for a personal billing account that's been approved.
        personal_billing_account = self.owned_billing_accounts.filter(
            ~Q(approved_at=None),
            account_type="p",
        ).first()

        if personal_billing_account is not None:
            log.debug(
                f"Approved own personal billing account id {personal_billing_account.id} found for user: {self.id}"
            )

        else:
            # Search for a personal billing account that's not been approved.
            personal_billing_account = self.owned_billing_accounts.filter(
                approved_at=None,
                account_type="p",
            ).first()

            if (
                personal_billing_account is None
                or not personal_billing_account.complete
            ):
                log.debug("No pending personal billing account.")
                return False

        log.debug(
            f"Own personal billing account {personal_billing_account.id} found for user: {self.id}"
        )

        # If there is a pending driver profile then return True.
        driver_profile_type = personal_billing_account.driver_profile_python_type
        driver_profiles = self.driver_profiles.instance_of(driver_profile_type).filter(
            ~Q(approved_to_drive=True),
            submitted_at__isnull=False,
        )
        for dp in driver_profiles:
            log.debug(
                f"Found appropriate pending driver profile {dp.id} for user {self.id} that is"
                f"compatible with own billing account: {personal_billing_account.id}."
            )
            return True

        # Check for approved driver profiles, and if there is one, then check if the
        # associated billing account is approved too.
        driver_profiles = self.driver_profiles.instance_of(driver_profile_type).filter(
            approved_to_drive=True,
            expires_at__gt=timezone.now(),
        )

        # FIXME: This doesn't actually check the DP goes with the BA. But we are working
        #        with the assumption by this stage that there is only one personal BA.
        #        Need to confirm whether that assumption is actually safe.
        for dp in driver_profiles:
            if personal_billing_account.approved_at is None:
                return True

        # If we made it this far then neither the driver profile nor billing accounts are pending approval.
        log.debug(f"Own personal account for user: {self.id} is not pending")
        return False

    def is_own_business_account_validated(self):
        """
        This method indicates whether the user has got a business driving account set
        up and approved and valid to drive which they personally own.

        :return: True if the user has a valid business driving account, otherwise False
        """
        log.debug(f"Checking if own business account is validated for user: {self.id}")

        # First check for a business billing account that's been approved.
        business_billing_account = self.owned_billing_accounts.filter(
            ~Q(approved_at=None),
            account_type="b",
        ).first()

        if business_billing_account is None:
            log.debug(f"No own business billing account found for user: {self.id}")
            return False

        log.debug(
            f"Own business billing account {business_billing_account.id} found for user: {self.id}"
        )

        # Then check for an approved driver profile of the appropriate type.
        driver_profile_type = business_billing_account.driver_profile_python_type
        driver_profile = (
            self.driver_profiles.instance_of(driver_profile_type)
            .filter(
                approved_to_drive=True,
                expires_at__gt=timezone.now(),
            )
            .first()
        )

        if driver_profile is None:
            log.debug(
                f"No valid driver profile found for user: {self.id} "
                f"that is compatible with own billing account: {business_billing_account.id}"
            )
            return False

        # If we made it this far then we're OK.
        log.debug(f"Own business account for user: {self.id} is fully validated")
        return True

    def is_own_business_account_pending_validation(self):
        log.debug(f"Checking if own business account is pending for user: {self.id}")

        # First check for a business billing account that's been approved.
        business_billing_account = self.owned_billing_accounts.filter(
            ~Q(approved_at=None),
            account_type="b",
        ).first()

        if business_billing_account is not None:
            log.debug(
                f"There's an already approved business billing account id {business_billing_account.id} for user {self.id}"
            )
            return False

        # Next check if there's an unapproved one that's complete
        business_billing_account = None
        business_billing_accounts = self.owned_billing_accounts.filter(
            approved_at=None,
            account_type="b",
        )

        for b in business_billing_accounts:
            if b.complete:
                business_billing_account = b
                break

        if business_billing_account is not None:
            log.debug("There's a business billing account that's pending.")
        else:
            log.debug("No complete/pending business billing accounts.")
            return False

        log.debug(
            f"Own business billing account {business_billing_account.id} found for user: {self.id}"
        )

        # If there is a pending driver profile then return True.
        driver_profile_type = business_billing_account.driver_profile_python_type
        driver_profiles = self.driver_profiles.instance_of(driver_profile_type).filter(
            ~Q(approved_to_drive=True),
            submitted_at__isnull=False,
        )
        for dp in driver_profiles:
            log.debug(
                f"Found appropriate pending driver profile for user {self.id} that is"
                f"compatible with own billing account: {business_billing_account.id}."
            )
            return True

        # Check for approved driver profiles, and if there is one, then check if the
        # associated billing account is approved too.
        driver_profiles = self.driver_profiles.instance_of(driver_profile_type).filter(
            approved_to_drive=True,
            expires_at__gt=timezone.now(),
        )

        # FIXME: This doesn't actually check the DP goes with the BA. But we are working
        #        with the assumption by this stage that there is only one personal BA.
        #        Need to confirm whether that assumption is actually safe.
        for dp in driver_profiles:
            if business_billing_account.approved_at is None:
                return True

        # If we made it this far then neither the driver profile nor billing accounts are pending approval.
        log.debug(f"Own business account for user: {self.id} is not pending")
        return False

    def is_own_business_billing_account_pending_validation(self):
        log.debug(f"Checking if own business biling account is pending for user: {self.id}")

        # First check for a business billing account that's been approved.
        business_billing_account = self.owned_billing_accounts.filter(
            ~Q(approved_at=None),
            account_type="b",
        ).first()

        if business_billing_account is not None:
            log.debug(
                f"There's an already approved business billing account id {business_billing_account.id} for user {self.id}"
            )
            return False

        # Next check if there's an unapproved one that's complete
        business_billing_account = None
        business_billing_accounts = self.owned_billing_accounts.filter(
            approved_at=None,
            account_type="b",
        )

        for b in business_billing_accounts:
            if b.complete:
                return True

        return False

    def has_pending_driver_profile(self):
        """
        This method checks whether the user has any driver profiles pending approval, and if
        so warns them that they won't be able to drive until this is resolved.

        :return: True if user has pending driver profiles, else False
        """
        log.debug(f"Checking if user {self.id} has a pending driver profile")
        driver_profiles = self.driver_profiles.filter(
            ~Q(approved_to_drive=True),
            submitted_at__isnull=False,
        )

        log.debug(
            f"User {self.id} has {driver_profiles.count()} pending driver profiles"
        )

        if driver_profiles.count() > 0:
            return True

        return False

    def can_make_bookings(self):
        """
        This method can be used to check whether this user has the rights to make
        bookings. Essentially, the user must have all their basic user data completed
        and validated, and must also have at least one billing account associated
        with them which has been approved.

        :return: True if the user can make bookings, otherwise False.
        """
        return (
            self.has_validated_mobile()
            and self.has_booking_permission_on_a_valid_billing_account()
        )

    def can_view_bookings(self):
        return (
            self.has_validated_mobile() and self.has_access_to_valid_billing_account()
        )

    def can_access_bookings(self):
        # As above, but can access bookings, not necessarily make them.
        return (
            self.has_validated_mobile()
            and self.has_access_to_valid_billing_account()
            and self.can_drive()
        )

    def has_valid_billing_account(self):
        for ba in self.owned_billing_accounts.all():
            if ba.valid:
                return True

    def has_booking_permission_on_a_valid_billing_account(self):
        if self.has_valid_billing_account():
            return True

        for bam in self.billingaccountmember_set.all():
            if bam.can_make_bookings and bam.billing_account.valid:
                return True

    def has_access_to_valid_billing_account(self):
        if self.has_valid_billing_account():
            return True

        for bam in self.billingaccountmember_set.all():
            if bam.billing_account.valid:
                return True
