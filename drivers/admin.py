from django.contrib import admin

from polymorphic.admin import (
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
)

from .models import DriverProfile, FullDriverProfile


class DriverProfileChildAdmin(PolymorphicChildModelAdmin):
    base_model = DriverProfile


@admin.register(FullDriverProfile)
class FullDriverProfileAdmin(DriverProfileChildAdmin):
    pass


@admin.register(DriverProfile)
class DriverProfileParentAdmin(PolymorphicParentModelAdmin):
    child_models = (FullDriverProfile,)
    list_filter = (PolymorphicChildModelFilter,)
