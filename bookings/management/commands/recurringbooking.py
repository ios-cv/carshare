import time

from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking
from billing.models import BillingAccount
from hardware.models import Vehicle
from users.models import User


class Command(BaseCommand):
    help = "Creates a recurring booking"

    def add_arguments(self, parser):
        parser.add_argument("user", type=int)
        parser.add_argument("billing_account", type=int)
        parser.add_argument("vehicle", type=int)
        parser.add_argument("start_time", type=str)
        parser.add_argument("end_time", type=str)
        parser.add_argument("start_date", type=str)
        parser.add_argument("end_date", type=str)

        parser.add_argument(
            "--mon",
            action="store_true",
        )
        parser.add_argument(
            "--tue",
            action="store_true",
        )
        parser.add_argument(
            "--wed",
            action="store_true",
        )
        parser.add_argument(
            "--thu",
            action="store_true",
        )
        parser.add_argument(
            "--fri",
            action="store_true",
        )
        parser.add_argument(
            "--sat",
            action="store_true",
        )
        parser.add_argument(
            "--sun",
            action="store_true",
        )

    def handle(self, *args, **options):
        user = User.objects.get(pk=options["user"])
        billing_account = BillingAccount.objects.get(pk=options["billing_account"])
        vehicle = Vehicle.objects.get(pk=options["vehicle"])

        start_time = parse(options["start_time"]).time()
        end_time = parse(options["end_time"]).time()

        start_date = parse(options["start_date"]).date()
        end_date = parse(options["end_date"]).date()

        dow = [
            options["mon"],
            options["tue"],
            options["wed"],
            options["thu"],
            options["fri"],
            options["sat"],
            options["sun"],
        ]

        self.stdout.write(
            self.style.NOTICE(
                f"Creating series of bookings for user: {user} with billing account {billing_account} and vehicle {vehicle.registration}"
            )
        )

        self.stdout.write(self.style.NOTICE(f"Times: {start_time} - {end_time}"))

        self.stdout.write(self.style.NOTICE(f"Dates: {start_date} - {end_date}"))

        self.stdout.write(self.style.NOTICE(f"Days of week: {dow}"))

        time.sleep(10)

        # Actually save the bookings.
        delta = end_date - start_date
        # FIXME: This needs to be made timezone aware - as at the moment it goes in as UTC.
        dates = [start_date + timezone.timedelta(days=i) for i in range(delta.days + 1)]

        for date in dates:
            if dow[date.weekday()]:
                self.stdout.write(
                    self.style.NOTICE(f"Writing booking for date: {date}")
                )

                start = timezone.datetime.combine(date, start_time)
                end = timezone.datetime.combine(date, end_time)

                try:
                    b = Booking.create_booking(
                        user, vehicle, start, end, billing_account
                    )

                    self.stdout.write(self.style.SUCCESS(f"Created booking {b}"))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to save booking for date: {date}. Exception {e}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Complete"))
