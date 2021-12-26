from django import forms

from allauth.account.forms import SignupForm

from .models import BillingAccount


class PersonalSignupForm(SignupForm):
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
        "username",
        "password1",
        "password2",
    ]

    def save(self, request):
        user = super(PersonalSignupForm, self).save(request)

        # Create the Billing Account here.
        billing_account = BillingAccount(
            owner=user,
            type=BillingAccount.PERSONAL,
        )
        billing_account.save()

        # Return the originally created user object.
        return user


class BusinessSignupForm(SignupForm):
    business_name = forms.CharField(
        label="Business name",
        max_length=100,
        min_length=2,
        widget=forms.TextInput(attrs={"placeholder": "Business name"}),
    )
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
        "business_name",
        "first_name",
        "last_name",
        "email",
        "username",
        "password1",
        "password2",
    ]

    def save(self, request):
        user = super(BusinessSignupForm, self).save(request)

        # Create the Billing Account here.
        billing_account = BillingAccount(
            owner=user,
            type=BillingAccount.BUSINESS,
            account_name=self.cleaned_data["business_name"],
        )
        billing_account.save()

        # Return the originally created user object.
        return user
