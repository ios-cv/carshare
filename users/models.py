import logging
import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone

log = logging.getLogger(__name__)


class User(AbstractUser):
    mobile = models.CharField(max_length=32, null=True)
    pending_mobile = models.CharField(max_length=32, null=True)
    mobile_verification_code = models.CharField(max_length=6, null=True)
    is_operator = models.BooleanField(default=False)

    class Meta:
        db_table = "user"

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
        """
        Find out if a user has any kind of currently valid driver profile in place.
        :return:
        """
        for dp in self.driver_profiles.filter(
            approved_to_drive=True, expires_at__gt=timezone.now()
        ):
            log.debug(
                f"User {self.id} has valid driver profile {dp} which expires at {dp.expires_at}"
            )
            return True

        log.debug(f"User {self.id} has no valid driver profiles")
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
            account_type="p"
        ).first()

        if personal_billing_account is None:
            log.debug(f"No own personal billing account found for user: {self.id}")
            return False

        log.debug(
            f"Own personal billing account {personal_billing_account.id} found for user: {self.id}"
        )

        if personal_billing_account.approved_at is None:
            log.debug(
                f"Own personal billing account {personal_billing_account.id} for user: {self.id} has not been approved."
            )
            return False

        # Then check for an approved driver profile of the appropriate type.
        driver_profile_type = personal_billing_account.driver_profile_python_type
        driver_profile = self.driver_profiles.instance_of(driver_profile_type).filter(
            approved_to_drive=True,
            expires_at__gt=timezone.now(),
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
            account_type="p"
        ).first()

        if personal_billing_account is None:
            log.debug(f"No own personal billing account found for user: {self.id}")
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
                f"Found appropriate pending driver profile for user {self.id} that is"
                f"compatible with own billing account: {personal_billing_account.id}."
            )
            return True

        # Check for approved driver profiles, and if there is one, then check if the
        # associated billing account is approved too.
        driver_profiles = self.driver_profiles.instance_of(driver_profile_type).filter(
            approved_to_drive=True,
            expires_at__gt=timezone.now(),
        )

        for dp in driver_profiles:
            if personal_billing_account.approved_at is None:
                return True

        # If we made it this far then neither the driver profile nor billing accounts are pending approval.
        log.debug(f"Own personal account for user: {self.id} is not pending")
        return False

    def can_make_bookings(self):
        """
        This method can be used to check whether this user has the rights to make
        bookings under any of their associated accounts.

        :return: True if the user can make bookings, otherwise False.
        """
        # TODO: Implement me properly with some check for a billing account that's valid and can make bookings!
        # Note: For now we require the user to be able to drive to make bookings. If we waive this requirement
        #       the UI will get very confusing because it would allow you to make bookings but then be unable to
        #       actually unlock the cars, which would be extremely weird and confusing.
        return (
            self.has_validated_mobile()
            and self.has_valid_billing_account()
            and self.can_drive()
        )

    def has_valid_billing_account(self):
        for ba in self.owned_billing_accounts.all():
            if ba.valid:
                return True
