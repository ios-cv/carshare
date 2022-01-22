from django.db import models
from django.utils import timezone

from users.models import User


class DriverProfile(models.Model):
    # Related User ID
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="driver_profiles"
    )

    # Full Legal Name (as per driving license)
    full_name = models.CharField(max_length=255, null=True)

    # Address
    address_line_1 = models.CharField(max_length=255, null=True)
    address_line_2 = models.CharField(max_length=255, null=True)
    address_line_3 = models.CharField(max_length=255, null=True)
    address_line_4 = models.CharField(max_length=255, null=True)
    postcode = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=255, null=True)

    # Date of Birth
    # FIXME: Do we need date of birth field?
    date_of_birth = models.DateField(null=True)

    # Licence Details
    licence_number = models.CharField(max_length=255, null=True)
    # FIXME: Do we need this place of issue field?
    licence_place_of_issue = models.CharField(max_length=255, null=True)
    licence_issue_date = models.DateField(null=True)
    licence_expiry_date = models.DateField(null=True)

    # Licence pictures
    licence_front = models.ImageField(null=True)
    licence_back = models.ImageField(null=True)
    licence_selfie = models.ImageField(null=True, upload_to="drivers/profiles/selfies")

    # DVLA Check Code
    licence_check_code = models.CharField(max_length=50, null=True)

    # Additional proof of Address
    # FIXME: Do we really need this?
    # proof_of_address = models.ImageField()

    # -------------------- Timestamps ---------------------------- #
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True)
    approved_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(null=True)

    # --------------------- Field Approvals ---------------------- #
    approved_full_name = models.BooleanField(null=True)
    approved_address = models.BooleanField(null=True)
    approved_date_of_birth = models.BooleanField(null=True)

    approved_licence_number = models.BooleanField(null=True)
    approved_licence_place_of_issue = models.BooleanField(null=True)
    approved_licence_issue_date = models.BooleanField(null=True)
    approved_licence_expiry_date = models.BooleanField(null=True)
    approved_licence_front = models.BooleanField(null=True)
    approved_licence_back = models.BooleanField(null=True)
    approved_licence_selfie = models.BooleanField(null=True)
    approved_driving_record = models.BooleanField(null=True)

    # ------------------- Final Approvals ---------------------- #
    dvla_summary = models.FileField()  # Added by staff
    approved_to_drive = models.BooleanField(null=True)  # Final approval to drive
    approved_by = models.ForeignKey(
        User, null=True, on_delete=models.PROTECT, related_name="+"
    )

    def __str__(self):
        return "Driver Profile [{}] for User: {}".format(self.id, self.user)

    @staticmethod
    def create(user):
        driver_profile = DriverProfile()
        driver_profile.user = user
        driver_profile.created_at = timezone.now()
        driver_profile.updated_at = timezone.now()
        return driver_profile

    @staticmethod
    def get_incomplete_driver_profile(user):
        try:
            incomplete_driver_profiles = DriverProfile.objects.filter(
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
        return self.approved_licence_selfie

    def is_driving_record_approved(self):
        return self.approved_driving_record
