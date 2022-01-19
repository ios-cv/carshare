from django.db import models


class Box(models.Model):
    """represents an individual in-vehicle car share control box"""

    serial = models.CharField(max_length=128, null=False)

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

    # The "model" of the vehicle in terms that dictate the firmware driver that
    # will be needed to interface with it.
    firmware_model = models.CharField(max_length=255)

    # The box installed in this vehicle.
    box = models.ForeignKey(Box, on_delete=models.PROTECT)

    # Cards that have "operator" privilege to always access this vehicle
    operator_cards = models.ManyToManyField(Card)

    def __str__(self):
        return "{} - {} [{}]".format(self.name, self.registration, self.id)
