import os
import uuid

from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils import timezone

from polymorphic.models import PolymorphicModel

from users.models import User


def uuid_file_name(file):
    ext = file.split(".")[-1]
    return "{}.{}".format(uuid.uuid4(), ext)


def licence_front_upload_to(instance, filename):
    return os.path.join("drivers/profiles/licence_front", uuid_file_name(filename))


def licence_back_upload_to(instance, filename):
    return os.path.join("drivers/profiles/licence_back", uuid_file_name(filename))


def licence_selfie_upload_to(instance, filename):
    return os.path.join("drivers/profiles/licence_selfie", uuid_file_name(filename))


def dvla_summary_upload_to(instance, filename):
    return os.path.join("drivers/profiles/dvla_summary", uuid_file_name(filename))


def proof_of_address_upload_to(instance, filename):
    return os.path.join("drivers/profiles/proof_of_address", uuid_file_name(filename))


class DriverProfile(PolymorphicModel):
    APPROVED = True
    REJECTED = False
    UNCHECKED = ""

    APPROVAL_CHOICES = [
        (APPROVED, "Approve"),
        (REJECTED, "Reject"),
        (UNCHECKED, "Unchecked"),
    ]

    # Related User ID
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="driver_profiles"
    )

    # -------------------- Timestamps ---------------------------- #
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    approved_to_drive = models.BooleanField(
        null=True, blank=True
    )  # Final approval to drive
    approved_by = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="+", blank=True
    )

    class Meta:
        db_table = "driver_profile"

    @admin.display(
        boolean=True,
        description="Submitted",
    )
    def admin__is_submitted(self):
        return self.submitted_at is not None

    @admin.display(
        boolean=True,
        description="Approved",
    )
    def admin__is_approved(self):
        return self.approved_to_drive


class ExternalDriverProfile(DriverProfile):
    commentary = models.TextField(blank=True)

    class Meta:
        db_table = "external_driver_profile"


class FullDriverProfile(DriverProfile):
    # Full Legal Name (as per driving license)
    full_name = models.CharField(max_length=255, null=True, blank=True)

    # Address
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    address_line_3 = models.CharField(max_length=255, null=True, blank=True)
    address_line_4 = models.CharField(max_length=255, null=True, blank=True)
    postcode = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)

    # Date of Birth
    date_of_birth = models.DateField(null=True, blank=True)

    # Licence Details
    licence_number = models.CharField(max_length=255, null=True, blank=True)
    licence_issue_date = models.DateField(null=True, blank=True)
    licence_expiry_date = models.DateField(null=True, blank=True)

    # Licence pictures
    licence_front = models.ImageField(
        null=True, blank=True, upload_to=licence_front_upload_to
    )
    licence_back = models.ImageField(
        null=True, blank=True, upload_to=licence_back_upload_to
    )
    licence_selfie = models.ImageField(
        null=True, upload_to=licence_selfie_upload_to, blank=True
    )

    # DVLA Check Code
    licence_check_code = models.CharField(max_length=50, null=True, blank=True)

    # Additional proof of Address
    proof_of_address = models.ImageField(
        null=True, upload_to=proof_of_address_upload_to, blank=True
    )

    # --------------------- Field Approvals ---------------------- #
    approved_full_name = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_address = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_date_of_birth = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )

    approved_licence_number = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_licence_issue_date = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_licence_expiry_date = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_licence_front = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_licence_back = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_licence_selfie = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_proof_of_address = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )
    approved_driving_record = models.BooleanField(
        null=True,
        blank=True,
        choices=DriverProfile.APPROVAL_CHOICES,
        default=DriverProfile.UNCHECKED,
    )

    # ------------------- Final Approvals ---------------------- #
    dvla_summary = models.FileField(
        null=True, blank=True, upload_to=dvla_summary_upload_to
    )  # Added by staff

    class Meta:
        db_table = "full_driver_profile"

    def __str__(self):
        return "Driver Profile [{}] for User: {}".format(self.id, self.user)

    @property
    def approval_fields(self):
        return [
            self.approved_full_name,
            self.approved_address,
            self.approved_date_of_birth,
            self.approved_licence_number,
            self.approved_licence_issue_date,
            self.approved_licence_expiry_date,
            self.approved_licence_front,
            self.approved_licence_back,
            self.approved_licence_selfie,
            self.approved_proof_of_address,
            self.approved_driving_record,
        ]

    @staticmethod
    def create(user):
        driver_profile = FullDriverProfile()
        driver_profile.user = user
        driver_profile.created_at = timezone.now()
        driver_profile.updated_at = timezone.now()
        return driver_profile

    @staticmethod
    def get_incomplete_driver_profile(user):
        try:
            incomplete_driver_profiles = FullDriverProfile.objects.filter(
                user=user, approved_at=None
            ).order_by("-created_at")
            return incomplete_driver_profiles[0]
        except IndexError:
            return None

    def reset_personal_details_approvals(self):
        self.approved_full_name = None
        self.approved_address = None
        self.approved_date_of_birth = None

    def reset_driving_licence_details_approvals(self):
        self.approved_licence_number = None
        self.approved_licence_issue_date = None
        self.approved_licence_expiry_date = None

    def reset_driving_licence_approvals(self):
        self.approved_licence_front = None
        self.approved_licence_back = None

    def reset_identity_approvals(self):
        self.approved_licence_selfie = None
        self.approved_proof_of_address = None

    def reset_driving_record_approvals(self):
        self.approved_driving_record = None

    def is_personal_details_approved(self):
        return (
            self.approved_full_name
            and self.approved_address
            and self.approved_date_of_birth
        )

    def is_driving_licence_details_approved(self):
        return (
            self.approved_licence_number
            and self.approved_licence_issue_date
            and self.approved_licence_expiry_date
        )

    def is_driving_licenced_approved(self):
        return self.approved_licence_front and self.approved_licence_back

    def is_identity_approved(self):
        return self.approved_licence_selfie and self.approved_proof_of_address

    def is_driving_record_approved(self):
        return self.approved_driving_record

    def can_profile_be_approved(self):
        """Returns True if the profile has everything approved in order to allow the operator
        to set overall approval on the profile, otherwise returns False."""
        return (
            self.is_personal_details_approved()
            and self.is_driving_licence_details_approved()
            and self.is_driving_licenced_approved()
            and self.is_identity_approved()
            and self.is_driving_record_approved()
        )

    def is_anything_rejected(self):
        """
        Helper method for the Backoffice to determine if any of the data in the driver profile
        has been rejected during the approval process.

        :return: True if anything is rejected, else False
        """
        if DriverProfile.REJECTED in self.approval_fields:
            return True

    def get_max_permitted_expiry_date(self):
        """
        Applies policy to the driver profile details to calculate the latest permitted expiry date of this profile
        if it is being approved for driving now.
        :return: the max permitted expiry date.
        """
        # TODO: look at date of birth and enforce a maximum age.
        return min(
            timezone.datetime.combine(
                self.licence_expiry_date,
                timezone.datetime.max.time(),
                timezone.utc,
            ),
            timezone.now() + timezone.timedelta(days=365),
        )


def get_all_pending_approval():
    """Returns a QuerySet encapsulating all the driver profiles that currently need operator approval."""
    return DriverProfile.objects.filter(~Q(submitted_at=None), approved_at=None)
