import re
import uuid

from django.core.exceptions import ValidationError
from django import forms
from django.utils import timezone

from .models import BillingAccount, BillingAccountMemberInvitation


class BusinessBillingAccountForm(forms.ModelForm):
    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields["account_name"].required = True
        self.fields["business_name"].required = True

    class Meta:
        model = BillingAccount
        fields = [
            "account_name",
            "business_name",
            "business_address_line_1",
            "business_address_line_2",
            "business_address_line_3",
            "business_address_line_4",
            "business_postcode",
            "business_tax_id",
        ]
        labels = {
            "account_name": "Account name",
            "business_name": "Business name",
            "business_tax_id": "Business VAT number",
        }
        help_texts = {
            "account_name": "A memorable name to identify this billing account. You will use this name whenever you make a booking to select which billing account it will be charged to.",
            "business_name": "The legal name of your business. This will be shown on your VAT invoices.",
            "business_address_line_1": "The address and post code provided here will appear on your VAT invoices.",
            "business_tax_id": "If you would like your VAT number shown on your invoices, please enter it here.",
        }

    def clean_business_tax_id(self):
        tax_id = self.cleaned_data["business_tax_id"]

        if tax_id is None:
            return None

        tax_id = tax_id.replace(" ", "")

        if not re.match(r"^[A-Z]{2}[0-9]{9}$", tax_id):
            raise ValidationError(
                "Your VAT number must be provided in the form 'GB123456789'"
            )

        return tax_id

    def save(self, commit=True):
        m = super().save(commit=False)
        m.owner = self.owner
        m.account_type = BillingAccount.BUSINESS
        m.driver_profile_type = BillingAccount.FULL
        if commit:
            m.save()
        return m


class InviteMemberForm(forms.ModelForm):
    def __init__(self, billing_account, inviting_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.billing_account = billing_account
        self.inviting_user = inviting_user

    class Meta:
        model = BillingAccountMemberInvitation
        fields = [
            "email",
            "can_make_bookings",
        ]
        labels = {"can_make_bookings": "Allow the user to make bookings"}
        help_texts = {
            "email": "The email address of the person to invite to join this billing account.",
            "can_make_bookings": "If selected, the invited user will be allowed to make bookings which"
            " will be charged to this billing account and can be accessed by all"
            " members of this billing account.",
        }

    def save(self, commit=True):
        m = super().save(commit=False)
        m.inviting_user = self.inviting_user
        m.billing_account = self.billing_account
        m.secret = uuid.uuid4()
        m.created_at = timezone.now()
        if commit:
            m.save()
        return m
