import logging

from crispy_forms.bootstrap import InlineCheckboxes
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils import timezone

from billing.models import BillingAccount, get_billing_accounts_suitable_for_booking
from hardware.models import VehicleType

from .models import MAX_BOOKING_END_DAYS

log = logging.getLogger(__name__)

MIN_BOOKING_LENGTH_MINS = 30


def gen_start_time(now):
    minutes = now.minute - (now.minute % 5)
    return now.replace(minute=minutes, second=0, microsecond=0) + timezone.timedelta(
        minutes=5
    )


def gen_end_time(now):
    start = gen_start_time(now)
    return start + timezone.timedelta(hours=1)


class VehicleTypeMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class BookingSearchForm(forms.Form):
    start = forms.SplitDateTimeField(
        label="Start time",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )
    end = forms.SplitDateTimeField(
        label="End time",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )
    vehicle_types = VehicleTypeMultipleChoiceField(
        label="Type of vehicle",
        queryset=VehicleType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "You must select at least one type of vehicle."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout("start", "end", InlineCheckboxes("vehicle_types"))

        self.fields["vehicle_types"].initial = VehicleType.objects.all()

        now = timezone.now()
        self.fields["start"].initial = gen_start_time(now)
        self.fields["end"].initial = gen_end_time(now)

    def clean_start(self):
        start = self.cleaned_data["start"]

        if start + timezone.timedelta(minutes=5) < timezone.now():
            raise ValidationError("Your booking must not start in the past.")

        if start < timezone.datetime(2023, 1, 15, 10, 0, 0, 0, timezone.utc):
            raise ValidationError(
                "Your booking must start after 10am on Sunday 15th January. Bookings before this date must be made in the old app."
            )

        return start

    def clean_end(self):
        end = self.cleaned_data["end"]

        if end > timezone.now() + timezone.timedelta(days=MAX_BOOKING_END_DAYS):
            raise ValidationError(
                f"Your can only make bookings up to {MAX_BOOKING_END_DAYS} days in the future."
            )

        return end

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if start and end and start >= end:
            raise ValidationError("You must choose an end time after your start time.")

        if (
            start
            and end
            and start + timezone.timedelta(minutes=MIN_BOOKING_LENGTH_MINS) > end
        ):
            raise ValidationError("Your booking must be at least 30 minutes long.")


class BookingDetailsForm(forms.Form):
    start = forms.DateTimeField(widget=widgets.HiddenInput)
    end = forms.DateTimeField(widget=widgets.HiddenInput)
    vehicle_id = forms.IntegerField(widget=widgets.HiddenInput)
    confirmed = forms.BooleanField(required=False, widget=widgets.HiddenInput)


class ConfirmBookingForm(forms.Form):
    start = forms.DateTimeField(widget=widgets.HiddenInput)
    end = forms.DateTimeField(widget=widgets.HiddenInput)
    vehicle_id = forms.IntegerField(widget=widgets.HiddenInput)
    confirmed = forms.BooleanField(required=False, widget=widgets.HiddenInput)
    billing_account = forms.ChoiceField(
        required=True,
        widget=widgets.Select,
        label="Select which billing account to charge this booking to:",
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        if len(args) > 0:
            self.set_billing_accounts(args[0]["end"])

    def set_billing_accounts(self, end_time):
        bas = get_billing_accounts_suitable_for_booking(self.user, end_time)

        choice_list = [("", "--------")]
        for ba in bas:
            if ba.account_type == BillingAccount.PERSONAL:
                label = f"{ba.owner.first_name} {ba.owner.last_name} (Personal)"
            elif ba.account_type == BillingAccount.BUSINESS:
                label = f"{ba.account_name} (Business)"
            else:
                log.error(
                    "Encountered unknown billing account type: {obj.account_type}"
                )
                label = "**unknown**"

            choice_list.append((ba.id, label))

        self.fields["billing_account"].choices = choice_list

    def clean_billing_account(self):
        ba_id = self.cleaned_data["billing_account"]

        if ba_id == "":
            raise ValidationError("Please select a billing account for this booking.")

        try:
            ba = BillingAccount.objects.get(pk=ba_id)
        except:
            raise ValidationError(
                "Please select a billing account you are allowed to make bookings for."
            )

        return ba

    def clean_start(self):
        start = self.cleaned_data["start"]

        if start + timezone.timedelta(minutes=5) < timezone.now():
            raise ValidationError("Your booking must not start in the past.")

        return start

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")
        ba = cleaned_data.get("billing_account")

        if start and end and start >= end:
            raise ValidationError("You must choose an end time after your start time.")

        if (
            start
            and end
            and start + timezone.timedelta(minutes=MIN_BOOKING_LENGTH_MINS) > end
        ):
            raise ValidationError("Your booking must be at least 30 minutes long.")

        if ba is not None:
            valid_bas = get_billing_accounts_suitable_for_booking(self.user, end)
            if ba not in valid_bas:
                raise ValidationError(
                    "You must choose a billing account you are allowed to make bookings with."
                )


class EditBookingForm(forms.Form):
    start = forms.SplitDateTimeField(
        label="Start time",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )
    end = forms.SplitDateTimeField(
        label="End time",
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time", "step": "60"},
            date_format="%Y-%m-%d",
            time_format="%H:%M",
        ),
    )

    def __init__(self, booking, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        self.fields["start"].initial = booking.reservation_time.lower
        self.fields["end"].initial = booking.reservation_time.upper

    def clean_start(self):
        start = self.cleaned_data["start"]

        now = timezone.now()

        if (
            now >= self.booking.reservation_time.lower
            and start != self.booking.reservation_time.lower
        ):
            raise ValidationError(
                "You can't change the start time of a booking that has already started."
            )

        if (
            start + timezone.timedelta(minutes=5) < timezone.now()
            and start != self.booking.reservation_time.lower
        ):
            raise ValidationError("Your booking must not start in the past.")

        return start

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if start and end and start >= end:
            raise ValidationError("You must choose an end time after your start time.")

        if (
            start
            and end
            and start + timezone.timedelta(minutes=MIN_BOOKING_LENGTH_MINS) > end
        ):
            raise ValidationError("Your booking must be at least 30 minutes long.")
