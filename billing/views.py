import stripe

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.models import BillingAccount


# Create your views here.


@login_required
def setup(request):
    context = {}
    # TODO: Only allow the owner of the billing account to do this.

    billing_account = request.user.billing_account

    intent = stripe.SetupIntent.create(
        customer=billing_account.stripe_customer_id,
        payment_method_types=["card"],
    )

    context["stripe_client_secret"] = intent.client_secret
    context["BASE_URL"] = settings.BASE_URL

    return render(request, "billing/setup.html", context)


@login_required
def setup_complete(request):
    context = {}
    # TODO: Only allow the owner of the billing account to do this.

    billing_account = request.user.billing_account

    return render(request, "billing/setup_complete.html", context)
