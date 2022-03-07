from crispy_forms.bootstrap import InlineCheckboxes
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.forms import widgets


class BookingSearchForm(forms.Form):
    OPTIONS = (("car", "Car"), ("combi", "Combi"), ("van", "Van"))

    start = forms.DateTimeField(label="Start Time")
    end = forms.DateTimeField(label="End Time")
    vehicle_types = forms.MultipleChoiceField(
        choices=OPTIONS, widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout("start", "end", InlineCheckboxes("vehicle_types"))


class ConfirmBookingForm(forms.Form):
    start = forms.DateTimeField(widget=widgets.HiddenInput)
    end = forms.DateTimeField(widget=widgets.HiddenInput)
    vehicle_id = forms.IntegerField(widget=widgets.HiddenInput)
    confirmed = forms.BooleanField(required=False, widget=widgets.HiddenInput)
