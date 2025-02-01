from allauth.utils import build_absolute_uri
from allauth.account.adapter import DefaultAccountAdapter

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def respond_email_verification_sent(self, request, user):
        return HttpResponseRedirect(reverse("email_verification_sent"))

    def get_email_confirmation_url(self, request, emailconfirmation):
        url = reverse("confirm_email", args=[emailconfirmation.key])
        ret = build_absolute_uri(request, url)
        return ret

    def render_mail(self, template_prefix, email, context, headers=None):
        # Set the REPLY-TO header on all emails.
        if settings.DEFAULT_REPLY_TO_EMAIL is not None:
            if headers is None:
                headers = {}
            headers["Reply-To"] = settings.DEFAULT_REPLY_TO_EMAIL

        return super().render_mail(template_prefix, email, context, headers)
