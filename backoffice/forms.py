from crispy_forms.bootstrap import InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.forms import ValidationError, ModelForm
from django.urls import reverse_lazy
from django.utils import timezone

from drivers.fields import CustomImageField
from drivers.models import DriverProfile, FullDriverProfile
from bookings.models import Booking


class DriverProfileReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address_line_2"].required = False
        self.fields["address_line_3"].required = False
        self.fields["address_line_4"].required = False

        self.helper_personal_info = FormHelper()
        self.helper_personal_info.form_tag = False
        self.helper_personal_info.layout = Layout(
            "full_name",
            "date_of_birth",
            "address_line_1",
            "address_line_2",
            "address_line_3",
            "address_line_4",
            "postcode",
        )

        self.helper_personal_info_approvals = FormHelper()
        self.helper_personal_info_approvals.form_tag = False
        self.helper_personal_info_approvals.layout = Layout(
            InlineRadios("approved_full_name"),
            InlineRadios("approved_address"),
            InlineRadios("approved_date_of_birth"),
        )

        self.helper_license_info = FormHelper()
        self.helper_license_info.form_tag = False
        self.helper_license_info.layout = Layout(
            "licence_number",
            "licence_issue_date",
            "licence_expiry_date",
        )

        self.helper_license_info_approvals = FormHelper()
        self.helper_license_info_approvals.form_tag = False
        self.helper_license_info_approvals.layout = Layout(
            InlineRadios("approved_licence_number"),
            InlineRadios("approved_licence_issue_date"),
            InlineRadios("approved_licence_expiry_date"),
        )

        self.helper_documents = FormHelper()
        self.helper_documents.form_tag = False
        self.helper_documents.layout = Layout(
            CustomImageField("licence_front"),
            CustomImageField("licence_back"),
            CustomImageField("licence_selfie"),
            CustomImageField("proof_of_address"),
        )

        self.helper_documents_approvals = FormHelper()
        self.helper_documents_approvals.form_tag = False
        self.helper_documents_approvals.layout = Layout(
            InlineRadios("approved_licence_front"),
            InlineRadios("approved_licence_back"),
            InlineRadios("approved_licence_selfie"),
            InlineRadios("approved_proof_of_address"),
        )

        self.helper_driving_record = FormHelper()
        self.helper_driving_record.form_tag = False
        self.helper_driving_record.layout = Layout(
            "licence_check_code",
            "dvla_summary",
        )

        self.helper_driving_record_approvals = FormHelper()
        self.helper_driving_record_approvals.form_tag = False
        self.helper_driving_record_approvals.layout = Layout(
            InlineRadios("approved_driving_record"),
        )

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
            "licence_number",
            "licence_issue_date",
            "licence_expiry_date",
            "licence_front",
            "licence_back",
            "licence_selfie",
            "proof_of_address",
            "licence_check_code",
            "approved_full_name",
            "approved_address",
            "approved_date_of_birth",
            "approved_licence_number",
            "approved_licence_issue_date",
            "approved_licence_expiry_date",
            "approved_licence_front",
            "approved_licence_back",
            "approved_licence_selfie",
            "approved_proof_of_address",
            "dvla_summary",
            "approved_driving_record",
        ]
        labels = {
            "full_name": "Full legal name",
            "licence_number": "Driving licence number",
            "licence_issue_date": "Driving licence date of issue",
            "licence_expiry_date": "Driving licence date of expiry",
            "licence_front": "Picture of the front of your driving licence",
            "licence_back": "Picture of the back of your driving licence",
            "licence_check_code": "DVLA check code",
        }
        help_texts = {
            "full_name": "Your full legal name as it appears on your driving licence.",
            "date_of_birth": "Your date of birth must match that shown on your driving licence.",
            "address_line_1": "Your address and postcode must match that shown on your driving licence.",
        }
        widgets = {
            "date_of_birth": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
            "licence_issue_date": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
            "licence_expiry_date": forms.widgets.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }


class DriverProfileApprovalForm(forms.Form):
    expiry = forms.DateField(
        label="Profile expires at:",
        widget=forms.DateInput(
            attrs={"type": "date"},
            format="%Y-%m-%d",
        ),
        required=True,
    )

    def __init__(self, driver_profile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver_profile = driver_profile

        self.fields["expiry"].initial = driver_profile.get_max_permitted_expiry_date()

    def clean_expiry(self):
        # TODO: incorporate this validation with the function above that's been moved to the driver profile for reuse.
        expiry = self.cleaned_data["expiry"]

        if expiry > self.driver_profile.licence_expiry_date:
            raise ValidationError(
                "Driver profile must expire before the driver's licence expiry date."
            )

        if expiry > (timezone.now() + timezone.timedelta(days=366)).date():
            raise ValidationError("Driver profile can only be valid for up to 1 year.")

        return expiry

    def save(self, user):
        self.driver_profile.expires_at = timezone.datetime.combine(
            self.cleaned_data["expiry"], timezone.datetime.max.time()
        )
        self.driver_profile.approved_at = timezone.now()
        self.driver_profile.approved_to_drive = True
        self.driver_profile.approved_by = user
        self.driver_profile.save()


class CloseBookingForm(forms.Form):
    should_lock = forms.BooleanField(required=False, initial=False)
    return_url = forms.CharField(
        required=False, initial=reverse_lazy("backoffice_home")
    )


class EditBookingForm(ModelForm):
    class Meta:
        model = Booking
        fields = [
            "vehicle",
            "state",
            "reservation_time",
            "actual_start_time",
            "actual_end_time",
        ]

    actual_start_time = forms.SplitDateTimeField(
        label="Actual start time",
        required=False,
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )
    actual_end_time = forms.SplitDateTimeField(
        label="Actual end time",
        required=False,
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )
