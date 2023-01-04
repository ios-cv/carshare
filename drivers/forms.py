from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.utils import timezone

from .fields import CustomImageField
from .models import FullDriverProfile


class DriverProfilePart1Form(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address_line_2"].required = False
        self.fields["address_line_3"].required = False
        self.fields["address_line_4"].required = False

    class Meta:
        model = FullDriverProfile
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
            "full_name": "Your full legal name.",
            "date_of_birth": "Your date of birth must match that shown on your driving licence.",
            "address_line_1": "Your address and postcode must match that shown on your driving licence.",
        }
        widgets = {
            "date_of_birth": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_personal_details_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart2Form(forms.ModelForm):
    class Meta:
        model = FullDriverProfile
        fields = ["licence_number", "licence_issue_date", "licence_expiry_date"]
        labels = {
            "licence_number": "Driving licence number",
            "licence_issue_date": "Driving licence date of issue",
            "licence_expiry_date": "Driving licence date of expiry",
        }
        help_texts = {
            "licence_number": "This is a mixture of letters and numbers, 18 characters in length and shown on the front of your driving license. Please enter it without any spaces.",
            "licence_issue_date": "This is shown on the front of your driving licence.",
            "licence_expiry_date": "This is shown on the front of your driving licence.",
        }
        widgets = {
            "licence_issue_date": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
            "licence_expiry_date": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_licence_details_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart3Form(forms.ModelForm):
    class Meta:
        model = FullDriverProfile
        fields = ["licence_front", "licence_back"]
        labels = {
            "licence_front": "Picture of the front of your driving licence",
            "licence_back": "Picture of the back of your driving licence",
        }
        help_texts = {
            "licence_front": "Please upload a photo showing the whole of the front of your driving licence so the information can be clearly seen.",
            "licence_back": "Please upload a photo showing the whole of the back of your driving licence so the information can be clearly seen.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            CustomImageField("licence_front"),
            CustomImageField("licence_back"),
        )

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_licence_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart4Form(forms.ModelForm):
    class Meta:
        model = FullDriverProfile
        fields = ["licence_selfie", "proof_of_address"]
        labels = {
            "licence_selfie": "Selfie showing you holding your driving licence",
            "proof_of_address": "Proof of address",
        }
        help_texts = {
            "licence_selfie": "Please provide a selfie holding your driving license, so that we can clearly see your face and the photo on your driving license side by side.",
            "proof_of_address": "Please upload a picture of an official document that proves your address, such as a bank statement, utility bill or council tax letter.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            CustomImageField("licence_selfie"),
            CustomImageField("proof_of_address"),
        )

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_identity_approvals()
        if commit:
            m.save()
        return m


class DriverProfilePart5Form(forms.ModelForm):
    class Meta:
        model = FullDriverProfile
        fields = ["licence_check_code"]
        labels = {
            "licence_check_code": "DVLA check code",
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.reset_driving_record_approvals()
        m.submitted_at = timezone.now()
        if commit:
            m.save()
        return m
