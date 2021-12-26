from django import forms

from allauth.account.forms import SignupForm

from .models import BillingAccount


class PersonalSignupForm(SignupForm):
    first_name = forms.CharField(
        label="First name",
        max_length=100,
        widget=forms.TextInput(
            attrs={"placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        label="Last name",
        max_length=100,
        widget=forms.TextInput(
            attrs={"placeholder": "Last Name"}
        ),
    )

    field_order = ['first_name', 'last_name', 'email', 'username', 'password1', 'password2']

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


class SignupBusiness(forms.Form):
    company_name = forms.CharField(label="Company Name", max_length=100)
    first_name = forms.CharField(label="First Name", max_length=100)
    last_name = forms.CharField(label="Last Name", max_length=100)
    email = forms.EmailField(label="Email", max_length=250)
    username = forms.CharField(label="Username", max_length=32)
