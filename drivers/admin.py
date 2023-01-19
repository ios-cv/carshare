from django.contrib import admin

from polymorphic.admin import (
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
)

from .models import DriverProfile, FullDriverProfile, ExternalDriverProfile


class DriverProfileChildAdmin(PolymorphicChildModelAdmin):
    base_model = DriverProfile


@admin.register(FullDriverProfile)
class FullDriverProfileAdmin(DriverProfileChildAdmin):
    pass


@admin.register(ExternalDriverProfile)
class ExternalDriverProfileAdmin(DriverProfileChildAdmin):
    pass


@admin.register(DriverProfile)
class DriverProfileParentAdmin(PolymorphicParentModelAdmin):
    child_models = (FullDriverProfile, ExternalDriverProfile)
    list_filter = (PolymorphicChildModelFilter,)
    list_display = (
        "id",
        "user",
        "polymorphic_ctype",
        "admin__is_submitted",
        "admin__is_approved",
        "expires_at",
    )
