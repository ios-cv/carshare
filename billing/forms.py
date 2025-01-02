import re
import uuid

from django.core.exceptions import ValidationError
from django import forms
from django.utils import timezone
from django.forms import ModelForm

from .models import BillingAccount, BillingAccountMemberInvitation
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, HTML


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
            "business_purchase_order",
        ]
        labels = {
            "account_name": "Account name",
            "business_name": "Business name",
            "business_tax_id": "Business VAT number",
            "business_purchase_order": "Purchase Order",
        }
        help_texts = {
            "account_name": "A memorable name to identify this billing account. You will use this name whenever you make a booking to select which billing account it will be charged to.",
            "business_name": "The legal name of your business. This will be shown on your VAT invoices.",
            "business_address_line_1": "The address and post code provided here will appear on your VAT invoices.",
            "business_tax_id": "If you would like your VAT number shown on your invoices, please enter it here in the format GB123456789",
            "business_purchase_order": "If you have a purchase order it will be displayed on your invoices, you may change this at any time.",
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


class UpdatePurchaseOrderForm(ModelForm):
    ba_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = BillingAccount
        fields = ["business_purchase_order"]
        labels = {"business_purchase_order": "Purchase order"}
        help_texts = {
            "business_purchase_order": "If you have a purchase order it will be displayed on your invoices, you may change this at any time."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business_purchase_order"].label_suffix = ""
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("ba_id", type="hidden"),
            HTML(
                "<h3 class='text-sm font-medium text-gray-500'>{{ ba.purchase_order_update_form.business_purchase_order.label_tag }}</h3>"
            ),
            Div(
                HTML(
                    "{{ ba.purchase_order_update_form.business_purchase_order.errors }}"
                ),
                css_class="text-xs text-red-500",
            ),
            Div(
                HTML(
                    "<input type='text' name='business_purchase_order' value='{{ ba.purchase_order_update_form.business_purchase_order.value }}' class='rounded-l-md mt-1 text-sm text-gray-900 h-full'>"
                ),
                HTML("<div class='{% if not ba.successfully_updated %}unchecked{% endif %} checkmark mt-2 icon--order-success'><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' width='32px' height='32px'>  <g fill='none' stroke='#0D9488' stroke-width='2'> <circle cx='77' cy='77' r='72' style='stroke-dasharray:480px, 480px; stroke-dashoffset: 960px;'></circle><circle id='colored' fill='#0D9488' cx='77' cy='77' r='72' style='stroke-dasharray:480px, 480px; stroke-dashoffset: 960px;'></circle><polyline class='st0' stroke='#fff' stroke-width='10' points='43.5,77.8 63.7,97.9 112.2,49.4 ' style='stroke-dasharray:100px, 100px; stroke-dashoffset: 200px;'/>   </g> </svg></div>"),
                Submit(
                    "submit",
                    "Update",
                    css_class="inline-flex items-center rounded-r-md border border-transparent bg-teal-600 px-3 h-full mt-1 text-sm font-medium leading-4 text-white shadow-sm hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2",
                ),
                css_class="flex flex-row gap-0 h-8",
            ),
        )
