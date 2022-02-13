from django.contrib import admin

from .models import Bay, Station, Box, Card, Vehicle, VehicleType

admin.site.register(Bay)
admin.site.register(Station)
admin.site.register(Box)
admin.site.register(Card)
admin.site.register(Vehicle)
admin.site.register(VehicleType)
