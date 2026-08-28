import uuid

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from psycopg2.extras import DateTimeTZRange

from billing.models import (
    BillingAccount,
    BillingAccountMember,
    BillingAccountMemberInvitation,
)
from bookings.models import Booking
from carshare.settings import POLICY_BUFFER_TIME
from drivers.models import DriverProfile, ExternalDriverProfile, FullDriverProfile
from hardware.models import (
    Bay,
    Box,
    Card,
    Firmware,
    Station,
    Telemetry,
    Vehicle,
    VehicleType,
)

DEFAULT_PASSWORD = "password"

PROFILE_APPROVAL_FIELDS = [
    "approved_full_name",
    "approved_address",
    "approved_date_of_birth",
    "approved_licence_number",
    "approved_licence_issue_date",
    "approved_licence_expiry_date",
    "approved_licence_front",
    "approved_licence_back",
    "approved_licence_selfie",
    "approved_proof_of_address",
    "approved_driving_record",
]


class Command(BaseCommand):
    help = (
        "Populates an empty database with a fully working data set across all "
        "models, suitable for integration testing, UI testing and manual review "
        "of new features. Run against an empty database, or pass --flush to "
        "wipe the existing data first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing data from the database before seeding.",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password to set for all seeded users (default: {DEFAULT_PASSWORD}).",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing database contents...")
            call_command("flush", interactive=False)
        elif get_user_model().objects.exists():
            raise CommandError(
                "The database already contains users. Seeding is only supported "
                "on an empty database. Re-run with --flush to wipe it first."
            )

        with transaction.atomic():
            self.seed(options["password"])

        self.print_summary(options["password"])

    def seed(self, password):
        now = timezone.now()
        # Anchor all bookings to the top of the current hour so the data set
        # always looks current, whenever it is generated.
        base = now.replace(minute=0, second=0, microsecond=0)

        self.stdout.write("Creating users...")
        admin = self.create_user(
            "admin",
            "Alice",
            "Admin",
            password,
            mobile="+447700900001",
            is_operator=True,
            is_staff=True,
            is_superuser=True,
        )
        operator = self.create_user(
            "operator",
            "Oscar",
            "Operator",
            password,
            mobile="+447700900002",
            is_operator=True,
            is_staff=True,
        )
        driver1 = self.create_user(
            "driver1", "Daisy", "Driver", password, mobile="+447700900003"
        )
        driver2 = self.create_user(
            "driver2", "Dylan", "Driver", password, mobile="+447700900004"
        )
        business_owner = self.create_user(
            "business", "Bella", "Boss", password, mobile="+447700900005"
        )
        external = self.create_user(
            "external", "Evan", "External", password, mobile="+447700900006"
        )
        pending = self.create_user(
            "pending", "Peter", "Pending", password, mobile="+447700900007"
        )
        # A brand-new user who has verified their email but not started the
        # driver profile or billing account signup flows yet.
        self.create_user("newuser", "Nina", "Newcomer", password)

        self.stdout.write("Creating driver profiles...")
        for i, user in enumerate([driver1, driver2, business_owner]):
            self.create_approved_full_profile(user, admin, now, licence_index=i)
        self.create_submitted_full_profile(pending, now)
        self.create_approved_external_profile(external, admin, now)

        self.stdout.write("Creating billing accounts...")
        personal1 = self.create_personal_account(driver1, now)
        personal2 = self.create_personal_account(driver2, now)
        self.create_personal_account(business_owner, now)
        # An account awaiting back-office approval.
        pending_account = BillingAccount.objects.create(
            owner=pending,
            account_type=BillingAccount.PERSONAL,
            driver_profile_type=BillingAccount.FULL,
            stripe_customer_id="cus_seed_pending",
            stripe_setup_intent_active=True,
        )
        self.add_member(pending, pending_account, now)

        business_account = BillingAccount.objects.create(
            owner=business_owner,
            account_type=BillingAccount.BUSINESS,
            driver_profile_type=BillingAccount.FULL,
            account_name="Tresco Stores",
            business_name="Tresco Stores Ltd",
            business_address_line_1="1 Harbour View",
            business_address_line_2="Tresco",
            business_postcode="TR24 0QQ",
            business_tax_id="GB123456789",
            stripe_customer_id="cus_seed_business",
            credit_account=True,
            approved_at=now,
        )
        self.add_member(business_owner, business_account, now)
        self.add_member(driver2, business_account, now)

        external_account = BillingAccount.objects.create(
            owner=business_owner,
            account_type=BillingAccount.BUSINESS,
            driver_profile_type=BillingAccount.EXTERNAL,
            account_name="Visiting Tradespeople",
            business_name="Tresco Stores Ltd",
            business_address_line_1="1 Harbour View",
            business_address_line_2="Tresco",
            business_postcode="TR24 0QQ",
            stripe_customer_id="cus_seed_external",
            credit_account=True,
            approved_at=now,
        )
        self.add_member(external, external_account, now)

        BillingAccountMemberInvitation.objects.create(
            inviting_user=business_owner,
            billing_account=business_account,
            can_make_bookings=True,
            email="invited@example.com",
            secret=uuid.uuid4(),
            created_at=now,
        )

        self.stdout.write("Creating hardware...")
        firmware = Firmware.objects.create(
            version=1,
            created_at=now,
            bin_file="firmware/1.bin",
            notes="Seeded firmware release.",
        )

        operator_card = Card.objects.create(
            key="00000000000000ff", operator=True, user=operator
        )
        driver1_card = Card.objects.create(key="0000000000000001", user=driver1)
        Card.objects.create(key="0000000000000002", user=driver2)
        Card.objects.create(key="0000000000000003", enabled=False)

        hugh_town = Station.objects.create(
            name="Hugh Town Car Park",
            location="https://maps.app.goo.gl/D2rNSWnJyJap7Mih6",
        )
        old_town = Station.objects.create(
            name="Old Town Community Hall",
            location="https://maps.app.goo.gl/D2rNSWnJyJap7Mih6",
        )
        bay1 = Bay.objects.create(name="Bay 1", station=hugh_town)
        bay2 = Bay.objects.create(name="Bay 2", station=hugh_town)
        bay3 = Bay.objects.create(name="Bay 1", station=old_town)

        car_type = VehicleType.objects.create(
            name="Car", description="Small electric car."
        )
        van_type = VehicleType.objects.create(
            name="Van", description="Electric panel van."
        )

        zoe = self.create_vehicle(
            name="Zennor",
            display_model="Renault Zoe",
            registration="EV24 AAA",
            vin="VF1AG000164000001",
            vehicle_type=car_type,
            bay=bay1,
            serial=1001,
            firmware=firmware,
            operator_card=operator_card,
            now=now,
        )
        kona = self.create_vehicle(
            name="Kelynack",
            display_model="Hyundai Kona Electric",
            registration="EV24 BBB",
            vin="KMHK281GFLU000002",
            vehicle_type=car_type,
            bay=bay2,
            serial=1002,
            firmware=firmware,
            operator_card=operator_card,
            now=now,
        )
        env200 = self.create_vehicle(
            name="Vellan",
            display_model="Nissan e-NV200",
            registration="EV24 CCC",
            vin="VSKHAAME0U0000003",
            vehicle_type=van_type,
            bay=bay3,
            serial=1003,
            firmware=firmware,
            operator_card=operator_card,
            now=now,
        )

        self.stdout.write("Creating telemetry...")
        for box, soc, odometer in [
            (zoe.box, 87, 10432),
            (kona.box, 54, 8211),
            (env200.box, 100, 15789),
        ]:
            Telemetry.objects.create(
                box=box,
                odometer_miles=odometer,
                doors_locked=box.locked,
                aux_battery_voltage=12.6,
                box_uptime_s=86400,
                box_free_heap_bytes=150000,
                soc_percent=soc,
            )

        self.stdout.write("Creating bookings...")
        day = timezone.timedelta(days=1)
        hour = timezone.timedelta(hours=1)

        # A completed and billed booking from last week.
        self.create_booking(
            driver1,
            zoe,
            personal1,
            base - 7 * day,
            base - 7 * day + 4 * hour,
            state=Booking.STATE_BILLED,
            actual_start_offset=5,
            actual_end_offset=-10,
            stripe_invoice_item_id="ii_seed_0001",
        )
        # A completed booking awaiting billing.
        self.create_booking(
            driver1,
            zoe,
            personal1,
            base - 2 * day,
            base - 2 * day + 3 * hour,
            state=Booking.STATE_ENDED,
            actual_start_offset=2,
            actual_end_offset=-20,
        )
        # A cancelled booking (overlaps the active one, which is allowed).
        self.create_booking(
            driver2,
            zoe,
            personal2,
            base - hour,
            base + hour,
            state=Booking.STATE_CANCELLED,
        )
        # A booking in progress right now: the driver has unlocked the car.
        active = self.create_booking(
            driver1,
            zoe,
            personal1,
            base - hour,
            base + 2 * hour,
            state=Booking.STATE_ACTIVE,
            actual_start_offset=3,
        )
        zoe.box.current_booking = active
        zoe.box.locked = False
        zoe.box.unlocked_by = driver1_card
        zoe.box.save()

        # A booking whose end time has passed without the vehicle being
        # returned.
        self.create_booking(
            driver2,
            env200,
            business_account,
            base - 5 * hour,
            base - 2 * hour,
            state=Booking.STATE_LATE,
            actual_start_offset=1,
        )
        # Upcoming bookings.
        self.create_booking(driver1, zoe, personal1, base + 4 * hour, base + 6 * hour)
        self.create_booking(
            driver2, kona, business_account, base + day, base + day + 3 * hour
        )
        self.create_booking(
            external,
            env200,
            external_account,
            base + 2 * day,
            base + 2 * day + 8 * hour,
        )

    def create_user(self, username, first_name, last_name, password, **kwargs):
        user = get_user_model().objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )
        EmailAddress.objects.create(
            user=user, email=user.email, primary=True, verified=True
        )
        return user

    def create_approved_full_profile(self, user, approved_by, now, licence_index=0):
        profile = FullDriverProfile.create(user)
        self.fill_full_profile(profile, now, licence_index)
        profile.submitted_at = now - timezone.timedelta(days=30)
        profile.approved_at = now - timezone.timedelta(days=29)
        profile.approved_to_drive = True
        profile.approved_by = approved_by
        for field in PROFILE_APPROVAL_FIELDS:
            setattr(profile, field, DriverProfile.APPROVED)
        profile.expires_at = profile.get_max_permitted_expiry_date()
        profile.save()
        return profile

    def create_submitted_full_profile(self, user, now):
        profile = FullDriverProfile.create(user)
        self.fill_full_profile(profile, now, licence_index=9)
        profile.submitted_at = now
        profile.save()
        return profile

    def fill_full_profile(self, profile, now, licence_index):
        profile.full_name = f"{profile.user.first_name} {profile.user.last_name}"
        profile.address_line_1 = f"{licence_index + 1} Church Street"
        profile.address_line_2 = "St Mary's"
        profile.address_line_3 = "Isles of Scilly"
        profile.postcode = "TR21 0JR"
        profile.country = "United Kingdom"
        profile.date_of_birth = timezone.datetime(
            1985, 6, licence_index + 1, tzinfo=timezone.get_current_timezone()
        ).date()
        profile.licence_number = f"DRIVE908156SM{licence_index}XY"
        profile.licence_issue_date = (now - timezone.timedelta(days=365 * 5)).date()
        profile.licence_expiry_date = (now + timezone.timedelta(days=365 * 5)).date()
        profile.licence_check_code = f"Ab cd ef {licence_index}{licence_index}"

    def create_approved_external_profile(self, user, approved_by, now):
        return ExternalDriverProfile.objects.create(
            user=user,
            created_at=now,
            updated_at=now,
            submitted_at=now - timezone.timedelta(days=10),
            approved_at=now - timezone.timedelta(days=9),
            expires_at=now + timezone.timedelta(days=365),
            approved_to_drive=True,
            approved_by=approved_by,
            commentary="Licence checked in person by the operator.",
        )

    def create_personal_account(self, user, now):
        account = BillingAccount.objects.create(
            owner=user,
            account_type=BillingAccount.PERSONAL,
            driver_profile_type=BillingAccount.FULL,
            stripe_customer_id=f"cus_seed_{user.username}",
            credit_account=True,
            approved_at=now,
        )
        self.add_member(user, account, now)
        return account

    def add_member(self, user, account, now):
        BillingAccountMember.objects.create(
            user=user,
            billing_account=account,
            created_at=now,
            updated_at=now,
            can_make_bookings=True,
        )

    def create_vehicle(
        self,
        name,
        display_model,
        registration,
        vin,
        vehicle_type,
        bay,
        serial,
        firmware,
        operator_card,
        now,
    ):
        box = Box.objects.create(
            serial=serial,
            secret=uuid.uuid4(),
            firmware_version=firmware.version,
            desired_firmware_version=firmware,
            last_seen_at=now,
        )
        vehicle = Vehicle.objects.create(
            name=name,
            display_model=display_model,
            registration=registration,
            vin=vin,
            vehicle_type=vehicle_type,
            bay=bay,
            firmware_model="maxbox-v1",
            box=box,
            description=f"{display_model} based at {bay.station.name}.",
        )
        vehicle.operator_cards.add(operator_card)
        return vehicle

    def create_booking(
        self,
        user,
        vehicle,
        billing_account,
        start,
        end,
        state=Booking.STATE_PENDING,
        actual_start_offset=None,
        actual_end_offset=None,
        stripe_invoice_item_id=None,
    ):
        booking = Booking(
            user=user,
            vehicle=vehicle,
            billing_account=billing_account,
            state=state,
            reservation_time=DateTimeTZRange(lower=start, upper=end),
            block_time=DateTimeTZRange(
                lower=start,
                upper=end + timezone.timedelta(minutes=POLICY_BUFFER_TIME),
            ),
            stripe_invoice_item_id=stripe_invoice_item_id,
        )
        if actual_start_offset is not None:
            booking.actual_start_time = start + timezone.timedelta(
                minutes=actual_start_offset
            )
        if actual_end_offset is not None:
            booking.actual_end_time = end + timezone.timedelta(
                minutes=actual_end_offset
            )
        booking.save()
        return booking

    def print_summary(self, password):
        self.stdout.write(self.style.SUCCESS("Database seeded successfully."))
        self.stdout.write("")
        self.stdout.write(f"All users have the password: {password}")
        self.stdout.write("")
        summary = [
            ("admin@example.com", "superuser and operator (backoffice + admin)"),
            ("operator@example.com", "operator (backoffice)"),
            ("driver1@example.com", "approved driver with past/active/future bookings"),
            ("driver2@example.com", "approved driver, member of business account"),
            ("business@example.com", "approved driver, owns the business accounts"),
            ("external@example.com", "external driver on the external account"),
            (
                "pending@example.com",
                "driver profile and billing account awaiting approval",
            ),
            (
                "newuser@example.com",
                "verified email only, no profile or billing account",
            ),
        ]
        for email, description in summary:
            self.stdout.write(f"  {email:24} {description}")
