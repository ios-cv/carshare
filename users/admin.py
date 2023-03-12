from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = UserAdmin.fieldsets + (
        (
            None,
            {
                "fields": (
                    "mobile",
                    "pending_mobile",
                    "mobile_verification_code",
                    "is_operator",
                )
            },
        ),
    )


admin.site.register(User, CustomUserAdmin)
