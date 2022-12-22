import logging
import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import BillingAccount, get_personal_billing_account_for_user

log = logging.getLogger(__name__)


@login_required
def setup(request, account_type):
    context = {
        "menu": "billing",
    }
    account_type = account_type.lower()
    user = request.user

    # Handle the "personal account" case first.
    if account_type == "personal":
        # Get the user's personal billing account
        billing_account = get_personal_billing_account_for_user(user)
        log.debug(f"Billing account for user {request.user} is {billing_account}")

        # If they don't have one, create one.
        if billing_account is None:
            customer = stripe.Customer.create(
                name=f"{user.first_name} {user.last_name}",
                email=user.email,
            )

            billing_account = BillingAccount(
                owner=user,
                account_type=BillingAccount.PERSONAL,
                driver_profile_type=BillingAccount.FULL,
                stripe_customer_id=customer.id,
            )

            billing_account.save()

        if billing_account.stripe_setup_intent_active:
            return redirect("drivers_create_profile")

        intent = stripe.SetupIntent.create(
            customer=billing_account.stripe_customer_id,
            payment_method_types=["card"],
        )

        context["stripe_client_secret"] = intent.client_secret
        context["BASE_URL"] = settings.BASE_URL
    else:
        # TODO: Implement me for business accounts.
        pass

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
