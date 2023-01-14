from django.contrib import admin

from .models import Bay, Station, Box, Card, Vehicle, VehicleType, Firmware


class BoxAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "serial",
        "firmware_version",
        "desired_firmware_version",
        "last_seen_at",
        "locked",
        "current_booking",
        "unlocked_by",
    )


class VehicleAdmin(admin.ModelAdmin):
    list_display = ("id", "registration", "vehicle_type", "box")


admin.site.register(Bay)
admin.site.register(Station)
admin.site.register(Box, BoxAdmin)
admin.site.register(Card)
admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(VehicleType)
admin.site.register(Firmware)
