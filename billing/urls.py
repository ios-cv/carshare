from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(
        r"^create_account/(?P<billing_account_type>(business|personal))/$",
        views.create_billing_account,
        name="billing_create_account",
    ),
    path(
        "set_payment/<int:billing_account>",
        views.set_payment,
        name="billing_set_payment",
    ),
    path("setup_complete", views.setup_complete, name="billing_setup_complete"),
    path("", views.profile_billing_accounts, name="billing_accounts_list"),
    path(
        "account/<int:billing_account>/members",
        views.profile_manage_members,
        name="billing_account_members",
    ),
    # FIXME: This should be a POST request not a GET.
    path(
        "account/<int:billing_account>/members/invitations/<int:invitation>/revoke",
        views.profile_revoke_invitation,
        name="billing_account_members_invitation_revoke",
    ),
    # FIXME: This should be a POST request not a GET.
    path(
        "account/<int:billing_account>/members/<int:member>/remove",
        views.profile_remove_member,
        name="billing_account_members_remove",
    ),
    path(
        "accept_invitation/<str:invitation>",
        views.accept_invitation,
        name="billing_account_accept_invitation",
    ),
    path(
        "/memberships",
        views.profile_other_account_memberships,
        name="billing_accounts_other_memberships",
    ),
]
