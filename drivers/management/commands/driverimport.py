import csv
import random
import string

from allauth.account.models import EmailAddress

from dateutil.parser import parse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from drivers.models import FullDriverProfile


class Command(BaseCommand):
    help = "Imports a CSV file of customer details to populate users and driver-profiles to the system."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    def handle(self, *args, **options):
        file_name = options["csv_file"]

        with open(file_name, mode="r", encoding="utf-8-sig") as f:
            r = csv.DictReader(f)

            now = timezone.now()

            for l in r:
                # Generate a username and password
                un = f"{l['first_name'].lower().replace(' ', '')}{l['last_name'].lower().replace(' ', '')}{random.randint(1, 1000)}"
                pw = "".join(random.choice(string.ascii_lowercase) for i in range(32))

                # Create the user
                u = get_user_model().objects.create_user(
                    username=un,
                    email=l["email"],
                    password=pw,
                    mobile=l["mobile"],
                    first_name=l["first_name"],
                    last_name=l["last_name"],
                )

                e = EmailAddress()
                e.user = u
                e.email = l["email"]
                e.primary = True
                e.verified = True
                e.save()

                d = FullDriverProfile()
                d.full_name = f"{l['first_name']} {l['last_name']}"
                d.address_line_1 = l["address_line_1"]
                d.address_line_2 = l["address_line_2"]
                d.address_line_3 = l["address_line_3"]
                d.address_line_4 = l["address_line_4"]
                d.postcode = l["postcode"]

                d.licence_number = l["licence_number"]
                d.licence_issue_date = parse(l["issue_date"], dayfirst=True).date()
                d.licence_expiry_date = parse(l["expiry_date"], dayfirst=True).date()

                d.user = u
                d.created_at = now
                d.updated_at = now
                d.submitted_at = now
                d.approved_at = now
                d.approved_to_drive = True

                d.expires_at = d.get_max_permitted_expiry_date()

                if d.expires_at < now + timezone.timedelta(days=364):
                    self.stdout.write(
                        self.style.ERROR(
                            f"Driver profile for {u.first_name} {u.last_name} [{u.id}] will expire on {d.expires_at.date()}"
                        )
                    )

                d.save()

                self.stdout.write(
                    self.style.NOTICE(
                        f"User [{u.id}] and driver profile [{d.id}] created for {d.full_name} - {u.email}."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Complete"))
