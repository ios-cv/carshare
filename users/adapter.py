from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponseRedirect
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def respond_email_verification_sent(self, request, user):
        return HttpResponseRedirect(reverse("email_verification_sent"))
