from django import forms


class BookingSearchForm(forms.Form):
    start = forms.DateTimeField(label="Start Time")
    end = forms.DateTimeField(label="End Time")
    car = forms.BooleanField(label="Car")
    combi = forms.BooleanField(label="Combi")
    van = forms.BooleanField(label="Van")
