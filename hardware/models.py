import os
import uuid

from django.db import models

from users.models import User


class Card(models.Model):
    """represents an individual RFID card"""

    # The hard coded ID of the card
    key = models.CharField(max_length=128)

    # Whether this card is allowed to be used or not.
    enabled = models.BooleanField(default=True, null=False)

    # Whether this is an "operator" type card (True) or an "ordinary" type card (False)
    operator = models.BooleanField(default=False, null=False)

    # Which user this card is assigned to.
    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="cards", null=True, blank=True
    )

    class Meta:
        db_table = "card"

    def __str__(self):
        return f"{self.key} [{self.id}]"


def firmware_upload_to(instance, filename):
    return os.path.join("hardware/firmware", uuid_file_name(filename))


class Firmware(models.Model):
    # The firmware version, represented by a single, unique integer.
    version = models.IntegerField(unique=True)

    # Uploaded at
    created_at = models.DateTimeField()

    # The firmware bin file.
    bin_file = models.FileField(upload_to=firmware_upload_to)

    # Notes for the admin / for reference
    notes = models.TextField()

    class Meta:
        db_table = "firmware"

    def __str__(self):
        return f"Firmware v{self.version} [{self.id}]"


class Box(models.Model):
    """represents an individual in-vehicle car share control box"""

    # The serial number of the box (typically it's MAC address)
    serial = models.BigIntegerField(null=False)

    # The box secret (a UUID)
    secret = models.UUIDField(null=False)

    # Whether the server considers the car to be locked or unlocked.
    locked = models.BooleanField(null=False, default=True, blank=True)

    # The current booking for the box.
    current_booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.PROTECT, null=True, blank=True
    )

    # The ID of the card that unlocked the box.
    unlocked_by = models.ForeignKey(
        Card, on_delete=models.PROTECT, null=True, blank=True
    )

    # The firmware version as reported by the box.
    firmware_version = models.IntegerField(default=0)

    # The desired firmware version, as specified by the admin.
    desired_firmware_version = models.ForeignKey(Firmware, on_delete=models.PROTECT)

    # The last time this box contacted us.
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "box"
        verbose_name_plural = "boxes"

    def __str__(self):
        return f"{self.serial} [{self.id}]"


class Station(models.Model):
    # The name of the station.
    name = models.CharField(max_length=100)
    location = models.URLField(null=True, blank=True)

    class Meta:
        db_table = "station"

    def __str__(self):
        return f"{self.name} [{self.id}]"


class Bay(models.Model):
    # The name of the bay.
    name = models.CharField(max_length=100)

    # The station this parking bay belongs to
    station = models.ForeignKey(Station, on_delete=models.PROTECT)

    class Meta:
        db_table = "bay"

    def __str__(self):
        return f"{self.name} [{self.id}]"


class VehicleType(models.Model):
    """represents the different types of vehicle"""

    name = models.CharField(max_length=36)
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "vehicle_type"

    def __str__(self):
        return f"{self.name} [{self.id}]"


def uuid_file_name(file):
    ext = file.split(".")[-1]
    return "{}.{}".format(uuid.uuid4(), ext)


def vehicle_picture_upload_to(instance, filename):
    return os.path.join("hardware/vehicles/picture", uuid_file_name(filename))


class Vehicle(models.Model):
    """represents an individual vehicle (car, van, etc.) in the fleet"""

    # Customer-facing name for this vehicle.
    name = models.CharField(max_length=100)

    # Customer-facing model details for this vehicle.
    display_model = models.CharField(max_length=100)

    # Registration Mark / Licence Plate.
    registration = models.CharField(max_length=8)

    # Vehicle Identification Number.
    vin = models.CharField(max_length=100)

    # Type of vehicle (customer facing)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.PROTECT)

    # Home parking bay
    bay = models.ForeignKey(Bay, on_delete=models.PROTECT)

    # The "model" of the vehicle in terms that dictate the firmware driver that
    # will be needed to interface with it.
    firmware_model = models.CharField(max_length=255)

    # The box installed in this vehicle.
    box = models.OneToOneField(Box, on_delete=models.PROTECT)

    # Cards that have "operator" privilege to always access this vehicle
    operator_cards = models.ManyToManyField(Card)

    # ETag for the operator_cards list of this vehicle (incremented whenever this is changed)
    operator_cards_etag = models.IntegerField(null=False, default=0)

    # Picture of the vehicle
    picture = models.ImageField(
        null=True,
        blank=True,
        upload_to=vehicle_picture_upload_to,
    )

    # A brief description of the vehicle
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "vehicle"

    def __str__(self):
        return f"{self.name} - {self.registration} [{self.id}]"
