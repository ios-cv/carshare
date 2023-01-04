import re

from allauth.utils import build_absolute_uri
from allauth.account.adapter import DefaultAccountAdapter
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
        # Fix non-configurable URLs in email templates to go to correct custom URLs.
        if "signup_url" in context:
            context["signup_url"] = build_absolute_uri(self.request, reverse("signup"))

        if "password_reset_url" in context:
            key = context["password_reset_url"].split("/key/", 1)[1]
            (uidb36, key) = re.match(
                r"^(?P<uidb36>[0-9A-Za-z]+)-(?P<key>.+)/$", key
            ).groups()
            print(key)
            context["password_reset_url"] = build_absolute_uri(
                self.request,
                reverse(
                    "users_password_reset_key", kwargs={"key": key, "uidb36": uidb36}
                ),
            )

        return super().render_mail(template_prefix, email, context, headers)
