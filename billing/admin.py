from django.contrib import admin

from .models import BillingAccount, BillingAccountMember, BillingAccountMemberInvitation


class BillingAccountAdmin(admin.ModelAdmin):
    list_filter = (
        "account_type",
        "credit_account",
        "driver_profile_type",
        "stripe_setup_intent_active",
    )
    list_display = (
        "id",
        "account_type",
        "credit_account",
        "owner",
        "account_name",
        "driver_profile_type",
        "admin__is_complete",
        "admin__is_valid",
    )


class BillingAccountMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "billing_account",
        "can_make_bookings",
    )


class BillingAccountMemberInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "billing_account",
        "inviting_user",
        "email",
        "can_make_bookings",
    )


# Register your models here.
admin.site.register(BillingAccount, BillingAccountAdmin)
admin.site.register(BillingAccountMember, BillingAccountMemberAdmin)
admin.site.register(BillingAccountMemberInvitation, BillingAccountMemberInvitationAdmin)
