from django.contrib import admin

from .models import Box, Card, Vehicle, VehicleType

admin.site.register(Box)
admin.site.register(Card)
admin.site.register(Vehicle)
admin.site.register(VehicleType)
