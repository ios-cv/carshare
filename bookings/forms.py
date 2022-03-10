from crispy_forms.bootstrap import InlineCheckboxes
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.forms import widgets

from hardware.models import VehicleType


class VehicleTypeMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class BookingSearchForm(forms.Form):
    start = forms.DateTimeField(label="Start Time")
    end = forms.DateTimeField(label="End Time")
    vehicle_types = VehicleTypeMultipleChoiceField(
        queryset=VehicleType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout("start", "end", InlineCheckboxes("vehicle_types"))
        self.fields["vehicle_types"].initial = VehicleType.objects.all()


class ConfirmBookingForm(forms.Form):
    start = forms.DateTimeField(widget=widgets.HiddenInput)
    end = forms.DateTimeField(widget=widgets.HiddenInput)
    vehicle_id = forms.IntegerField(widget=widgets.HiddenInput)
    confirmed = forms.BooleanField(required=False, widget=widgets.HiddenInput)
