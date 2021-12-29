from django.db import models

from users.models import User


class DriverProfile(models.Model):
    # Related User ID
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="driver_profiles")

    # Full Legal Name (as per driving license)
    full_name = models.CharField(max_length=255)

    # Address
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255)
    address_line_3 = models.CharField(max_length=255)
    address_line_4 = models.CharField(max_length=255)
    postcode = models.CharField(max_length=255)
    country = models.CharField(max_length=255)

    # Date of Birth
    # FIXME: Do we need date of birth field?
    date_of_birth = models.DateField()

    # Licence Details
    licence_number = models.CharField(max_length=255)
    # FIXME: Do we need this place of issue field?
    licence_place_of_issue = models.CharField(max_length=255)
    licence_issue_date = models.DateField()
    licence_expiry_date = models.DateField()

    # Licence pictures
    licence_front = models.ImageField()
    licence_back = models.ImageField()
    licence_selfie = models.ImageField()

    # DVLA Check Code
    licence_check_code = models.CharField(max_length=50)

    # Additional proof of Address
    # FIXME: Do we really need this?
    # proof_of_address = models.ImageField()

    # -------------------- Timestamps ---------------------------- #
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    approved_at = models.DateTimeField()
    expires_at = models.DateTimeField()

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
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")

