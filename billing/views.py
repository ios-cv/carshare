import copy
import logging
from django.forms import model_to_dict
import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .forms import BusinessBillingAccountForm, InviteMemberForm, UpdatePurchaseOrderForm
from .models import (
    BillingAccount,
    get_personal_billing_account_for_user,
    BillingAccountMemberInvitation,
    BillingAccountMember,
)

log = logging.getLogger(__name__)


@login_required
def create_billing_account(request, billing_account_type):
    initial = False
    if "initial" in request.GET:
        initial = True

    billing_account_type = billing_account_type.lower()

    context = {
        "menu": "billing",
        "account_type": billing_account_type,
        "hide_driver_profile_warnings": True,
    }

    if billing_account_type == "personal":
        # See if the user has a personal billing account yet.
        billing_account = get_personal_billing_account_for_user(request.user)
        log.debug(f"Billing account for user {request.user} is {billing_account}")

        # If they don't have one, create one.
        if billing_account is None:
            billing_account = BillingAccount(
                owner=request.user,
                account_type=BillingAccount.PERSONAL,
                driver_profile_type=BillingAccount.FULL,
            )

            billing_account.save()

        return redirect("billing_set_payment", billing_account=billing_account.id)

    elif billing_account_type == "business":
        # If the "initial" flag is set, only create a new one if there isn't one already.
        bba = request.user.owned_billing_accounts.filter(
            account_type=BillingAccount.BUSINESS
        )
        if bba.count() > 0 and initial:
            return redirect("billing_set_payment", billing_account=bba.first().id)

        if request.method == "POST":
            form = BusinessBillingAccountForm(request.user, request.POST)
            if form.is_valid():
                ba = form.save()
                return redirect("billing_set_payment", billing_account=ba.id)
        else:
            form = BusinessBillingAccountForm(request.user)

        context["form"] = form
        return render(request, "billing/create_billing_account.html", context)

    return redirect("users_incomplete")


@login_required
def set_payment(request, billing_account):
    billing_account = BillingAccount.objects.get(pk=billing_account)
    user = request.user

    # Security - check this user actually owns the billing account.
    if billing_account.owner != user:
        return redirect("users_incomplete")

    context = {
        "menu": "billing",
        "billing_account": billing_account,
        "hide_driver_profile_warnings": True,
    }

    # Handle the "personal account" case first.
    if billing_account.account_type == BillingAccount.PERSONAL:
        # Check if the stripe customer ID is set, and if not, set it.
        if billing_account.stripe_customer_id is None:
            customer = stripe.Customer.create(
                name=f"{user.first_name} {user.last_name}",
                email=user.email,
            )

            billing_account.stripe_customer_id = customer.id
            billing_account.save()

    # Now handle the business account case.
    elif billing_account.account_type == BillingAccount.BUSINESS:
        # Check if the stripe customer ID is set, and if not, set it.
        if billing_account.stripe_customer_id is None:
            customer_kwargs = {
                "name": f"{billing_account.business_name}",
                "email": user.email,
                "address": {
                    "line1": billing_account.business_address_line_1,
                    "line2": billing_account.business_address_line_2,
                    "city": billing_account.business_address_line_3,
                    "state": billing_account.business_address_line_4,
                    "postal_code": billing_account.business_postcode,
                    "country": "GB",
                },
            }

            if billing_account.business_tax_id is not None:
                customer_kwargs["tax_id_data"] = [
                    {
                        "type": "gb_vat",
                        "value": billing_account.business_tax_id,
                    },
                ]
            customer = stripe.Customer.create(**customer_kwargs)

            billing_account.stripe_customer_id = customer.id
            billing_account.save()

    # And redirect if it's not a recognised type.
    else:
        return redirect("users_incomplete")

    if billing_account.stripe_setup_intent_active:
        # FIXME: Should redirect location depend on whether this is the initial setup or not?
        return redirect("billing_create_account_complete")

    intent = stripe.SetupIntent.create(
        customer=billing_account.stripe_customer_id,
        payment_method_types=["card"],
    )

    context["stripe_client_secret"] = intent.client_secret
    context["stripe_public_key"] = settings.STRIPE_PUBLIC_KEY
    context["BASE_URL"] = settings.BASE_URL

    return render(request, "billing/set_payment.html", context)


@login_required
def setup_complete(request):
    context = {
        "menu": "billing",
        "hide_driver_profile_warnings": True,
    }

    intent = stripe.SetupIntent.retrieve(request.GET["setup_intent"])
    if intent.status == "succeeded":
        billing_account = BillingAccount.by_stripe_customer_id(intent.customer)
        if billing_account.owner != request.user:
            # Security - user must own billing account to modify it.
            return redirect("users_incomplete")
        billing_account.stripe_setup_intent_active = True
        billing_account.save()

        if billing_account.account_type == BillingAccount.BUSINESS:
            return redirect("billing_create_account_complete")
        else:
            return redirect("drivers_create_profile")

    return render(request, "billing/setup_complete.html", context)


@login_required
def create_account_complete(request):
    context = {
        "menu": "billing",
        "hide_driver_profile_warnings": True,
    }

    return render(request, "billing/create_account_complete.html", context)


@login_required
def profile_billing_accounts(request):
    billing_accounts = request.user.owned_billing_accounts.all()
    update_success = False
    ba_id = None
    if request.method == "POST":
        form = UpdatePurchaseOrderForm(request.POST)
        if form.is_valid():
            ba_id = form.cleaned_data["ba_id"]
            updated_billing_account = get_object_or_404(BillingAccount, id=ba_id)
            if updated_billing_account in billing_accounts:
                update_purchase_order_form = UpdatePurchaseOrderForm(
                    request.POST,
                    instance=updated_billing_account,
                )
                update_purchase_order_form.save()
                update_success = True
        else:
            ba_id = form.cleaned_data["ba_id"]

    for billing_account in billing_accounts:
        if ba_id != None and billing_account.id == ba_id:
            billing_account.purchase_order_update_form = form
            billing_account.successfully_updated = update_success
        else:
            billing_account.purchase_order_update_form = UpdatePurchaseOrderForm(
                initial={
                    "ba_id": billing_account.id,
                    "business_purchase_order": billing_account.business_purchase_order,
                }
            )
            billing_account.successfully_updated = False

    context = {
        "menu": "profile",
        "profile_menu": "billing_accounts",
        "billing_accounts": billing_accounts,
    }

    return render(request, "billing/profile_billing_accounts.html", context)


@login_required
def profile_manage_members(request, billing_account):
    context = {
        "menu": "profile",
        "profile_menu": "billing_accounts",
    }

    billing_account = BillingAccount.objects.get(pk=billing_account)

    if billing_account.owner != request.user:
        # Security, don't allow access to the billing account if the user doesn't own it.
        return redirect("users_incomplete")

    if request.method == "POST":
        form = InviteMemberForm(billing_account, request.user, request.POST)
        if form.is_valid():
            # TODO: If form is submitted, generate the email to the invited member.
            invite = form.save()

            email_ctx = {
                "user": request.user,
                "billing_account": billing_account,
                "invite_url": request.build_absolute_uri(
                    reverse("billing_account_accept_invitation", args=(invite.secret,))
                ),
                "signup_url": request.build_absolute_uri(reverse("account_signup")),
            }
            email = EmailMessage(
                "Invitation to join a billing account on GO-EV Car Share",
                render_to_string(
                    "billing/emails/billing_account_invite.txt", email_ctx
                ),
                None,
                [invite.email],
                reply_to=(
                    None
                    if settings.DEFAULT_REPLY_TO_EMAIL is None
                    else [settings.DEFAULT_REPLY_TO_EMAIL]
                ),
            )
            email.send(fail_silently=False)
            form = InviteMemberForm(billing_account, request.user)

    else:
        form = InviteMemberForm(billing_account, request.user)

    context["form"] = form
    context["billing_account"] = billing_account

    return render(request, "billing/profile_manage_members.html", context)


@login_required
def profile_revoke_invitation(request, billing_account, invitation):
    billing_account = BillingAccount.objects.get(pk=billing_account)
    invitation = BillingAccountMemberInvitation.objects.get(pk=invitation)

    # Authorise user.
    if not (
        invitation.inviting_user == request.user
        or (
            billing_account.owner == request.user
            and billing_account == invitation.billing_account
        )
    ):
        # TODO: Redirect somewhere more appropriate
        return redirect("users_incomplete")

    # TODO: toast to tell user it is done.
    invitation.delete()

    return redirect("billing_account_members", billing_account=billing_account.id)


@login_required
def profile_remove_member(request, billing_account, member):
    billing_account = BillingAccount.objects.get(pk=billing_account)
    member = BillingAccountMember.objects.get(pk=member)

    # Authorise user.
    if not (
        billing_account.owner == request.user
        and billing_account == member.billing_account
    ):
        # TODO: Redirect somewhere more appropriate
        return redirect("users_incomplete")

    # TODO: toast to tell user it is done.
    member.delete()

    return redirect("billing_account_members", billing_account=billing_account.id)


@login_required
def accept_invitation(request, invitation):
    try:
        invitation = BillingAccountMemberInvitation.objects.get(secret=invitation)
    except:
        return redirect("users_incomplete")

    if invitation.billing_account.owner == request.user:
        # TODO: display message to user.
        return redirect("users_incomplete")
    else:
        member = BillingAccountMember()

        member.can_make_bookings = invitation.can_make_bookings
        member.billing_account = invitation.billing_account
        member.user = request.user
        member.created_at = timezone.now()
        member.updated_at = timezone.now()

        member.save()
        invitation.delete()

    # TODO: Return to some page in the billing area instead.
    return redirect("users_incomplete")


@login_required
def profile_other_account_memberships(request):
    context = {
        "menu": "profile",
        "profile_menu": "memberships",
    }
    return render(request, "billing/profile_other_account_memberships.html", context)
