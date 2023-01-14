from django.contrib import admin
from django import forms
from .models import Booking


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        exclude = [""]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
