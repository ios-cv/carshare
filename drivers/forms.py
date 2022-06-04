from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.utils import timezone

from .fields import CustomImageField
from .models import DriverProfile


class DriverProfilePart1Form(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address_line_2"].required = False
        self.fields["address_line_3"].required = False
        self.fields["address_line_4"].required = False

    class Meta:
        model = DriverProfile
        fields = [
            "full_name",
            "date_of_birth",
            "address_line_1",
            "address_line_2",
            "address_line_3",
            "address_line_4",
            "postcode",
        ]
        labels = {
            "full_name": "Full legal name",
        }
        help_texts = {
            "full_name": "Your full legal name as it appears on your driving licence.",
            "date_of_birth": "Your date of birth must match that shown on your driving licence.",
            "address_line_1": "Your address and postcode must match that shown on your driving licence.",
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_personal_details_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart2Form(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["licence_number", "licence_issue_date", "licence_expiry_date"]
        labels = {
            "licence_number": "Driving Licence Number",
            "licence_issue_date": "Driving Licence Issue Date",
            "licence_expiry_date": "Driving Licence Expiry Date",
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_licence_details_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart3Form(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["licence_front", "licence_back"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            CustomImageField('licence_front'),
            CustomImageField('licence_back'),
        )

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_licence_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart4Form(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["licence_selfie"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            CustomImageField('licence_selfie'),
        )

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_identity_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart5Form(forms.ModelForm):
    class Meta:
        model = DriverProfile
        fields = ["licence_check_code"]

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_record_approvals()
        m.submitted_at = timezone.now()
        if commit:
            m.save()
        return m
