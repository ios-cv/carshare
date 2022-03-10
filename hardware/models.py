from django.db import models


class Box(models.Model):
    """represents an individual in-vehicle car share control box"""

    # The serial number of the box (typically it's MAC address)
    serial = models.BigIntegerField(null=False)

    # The box secret (a UUID)
    secret = models.UUIDField(null=False)

    class Meta:
        verbose_name_plural = "boxes"

    def __str__(self):
        return "{}".format(self.serial)


class Card(models.Model):
    """represents an individual RFID card"""

    # The hard coded ID of the card
    key = models.CharField(max_length=128)

    # Whether this card is allowed to be used or not.
    enabled = models.BooleanField(default=True, null=False)

    # Whether this is an "operator" type card (True) or an "ordinary" type card (False)
    operator = models.BooleanField(default=False, null=False)

    def __str__(self):
        return "{}".format(self.key)


class Station(models.Model):
    # The name of the station.
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Bay(models.Model):
    # The name of the bay.
    name = models.CharField(max_length=100)

    # The station this parking bay belongs to
    station = models.ForeignKey(Station, on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class VehicleType(models.Model):
    """represents the different types of vehicle"""

    name = models.CharField(max_length=36)

    def __str__(self):
        return "{} [{}]".format(self.name, self.id)


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
    type = models.ForeignKey(VehicleType, on_delete=models.PROTECT)

    # Home parking bay
    # FIXME: Make this not null before production
    bay = models.ForeignKey(Bay, on_delete=models.PROTECT, null=True)

    # The "model" of the vehicle in terms that dictate the firmware driver that
    # will be needed to interface with it.
    firmware_model = models.CharField(max_length=255)

    # The box installed in this vehicle.
    box = models.OneToOneField(Box, on_delete=models.PROTECT)

    # Cards that have "operator" privilege to always access this vehicle
    operator_cards = models.ManyToManyField(Card)

    # ETag for the operator_cards list of this vehicle (incremented whenever this is changed)
    operator_cards_etag = models.IntegerField(null=False, default=0)

    def __str__(self):
        return "{} - {} [{}]".format(self.name, self.registration, self.id)
