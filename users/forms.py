from django import forms

from allauth.account.forms import SignupForm as AllAuthSignupForm
from allauth.account.forms import LoginForm as AllAuthLoginForm

from crispy_forms.bootstrap import InlineField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from .models import User


class LoginForm(AllAuthLoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout("login", "password", InlineField("remember"))


class SignupForm(AllAuthSignupForm):
    first_name = forms.CharField(
        label="First name",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "First name"}),
    )
    last_name = forms.CharField(
        label="Last name",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Last name"}),
    )

    field_order = [
        "first_name",
        "last_name",
        "email",
        "password1",
        "password2",
    ]

    def save(self, request):
        # FIXME: Proper error handling / rollback if one part of the chain of actions here fails.
        user = super().save(request)

        # TODO: Move this to wherever we create the stripe account in future.
        # customer = stripe.Customer.create(
        #    name=f"{user.first_name} {user.last_name}",
        #    email=user.email,
        # )

        user.save()

        # Return the originally created user object.
        return user


class AddMobileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "pending_mobile",
        ]
        labels = {
            "pending_mobile": "Mobile number",
        }
        help_texts = {
            "pending_mobile": "Enter your UK mobile number, e.g.: 07890123456"
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.mobile_verification_code = User.generate_verification_code()
        if commit:
            m.save()
        return m


class VerifyMobileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "mobile_verification_code",
        ]
        labels = {
            "mobile_verification_code": "Verification code",
        }
        help_texts = {
            "mobile_verification_code": "Enter the 6-digit code you received in a text message to your mobile phone."
        }

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("mobile_verification_code")
            != self.instance.mobile_verification_code
        ):
            raise forms.ValidationError("Verification code is incorrect.")
        return cleaned_data

    def save(self, commit=True):
        m = super().save(commit=False)
        m.mobile = m.pending_mobile
        m.mobile_verification_code = None
        m.pending_mobile = None
        if commit:
            m.save()
        return m
