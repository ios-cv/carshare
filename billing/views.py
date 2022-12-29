import logging
import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import BillingAccount, get_personal_billing_account_for_user

log = logging.getLogger(__name__)


@login_required
def create_billing_account(request, billing_account_type):
    billing_account_type = billing_account_type.lower()

    context = {
        "menu": "billing",
        "account_type": billing_account_type,
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
        # TODO: Always show the form to create a new business account.

        # TODO: On form submitted, save the billing account and forward to stripe.

        # TODO: Then, redirect to the billing_set_account_card page.

        pass

    return redirect("users_incomplete")


@login_required
def set_payment(request, billing_account):
    billing_account = BillingAccount.objects.get(pk=billing_account)
    user = request.user

    context = {
        "menu": "billing",
        "billing_account": billing_account,
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
            customer = stripe.Customer.create(
                name=f"{billing_account.business_name}",
                email=user.email,
                address={
                    "line1": billing_account.business_address_line_1,
                    "line2": billing_account.business_address_line_2,
                    "city": billing_account.business_address_line_3,
                    "state": billing_account.business_address_line_4,
                    "postal_code": billing_account.business_postcode,
                },
            )

            billing_account.stripe_customer_id = customer.id
            billing_account.save()

    # And redirect if it's not a recognised type.
    else:
        return redirect("users_incomplete")

    if billing_account.stripe_setup_intent_active:
        # FIXME: Redirect location should depend on whether this is the initial setup or not.
        return redirect("drivers_create_profile")

    intent = stripe.SetupIntent.create(
        customer=billing_account.stripe_customer_id,
        payment_method_types=["card"],
    )

    context["stripe_client_secret"] = intent.client_secret
    context["BASE_URL"] = settings.BASE_URL

    return render(request, "billing/setup.html", context)


@login_required
def setup_complete(request):
    context = {
        "menu": "billing",
    }
    # TODO: Only allow the owner of the billing account to do this.

    intent = stripe.SetupIntent.retrieve(request.GET["setup_intent"])
    if intent.status == "succeeded":
        billing_account = BillingAccount.by_stripe_customer_id(intent.customer)
        billing_account.stripe_setup_intent_active = True
        billing_account.save()

        if billing_account.account_type == BillingAccount.PERSONAL:
            return redirect("drivers_create_profile")

    return render(request, "billing/setup_complete.html", context)
