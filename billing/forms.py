from django import forms

from .models import BillingAccount


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

    def save(self, commit=True):
        m = super().save(commit=False)
        m.owner = self.owner
        m.account_type = BillingAccount.BUSINESS
        m.driver_profile_type = BillingAccount.FULL
        if commit:
            m.save()
        return m
