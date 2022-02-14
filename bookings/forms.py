from django import forms
from django.forms import widgets


class BookingSearchForm(forms.Form):
    start = forms.DateTimeField(label="Start Time")
    end = forms.DateTimeField(label="End Time")
    car = forms.BooleanField(label="Car")
    combi = forms.BooleanField(label="Combi")
    van = forms.BooleanField(label="Van")


class ConfirmBookingForm(forms.Form):
    start = forms.DateTimeField(widget=widgets.HiddenInput)
    end = forms.DateTimeField(widget=widgets.HiddenInput)
    vehicle_id = forms.IntegerField(widget=widgets.HiddenInput)
    confirmed = forms.BooleanField(required=False, widget=widgets.HiddenInput)
