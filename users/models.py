import random

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    mobile = models.CharField(max_length=32, null=True)
    pending_mobile = models.CharField(max_length=32, null=True)
    mobile_verification_code = models.CharField(max_length=6, null=True)

    @staticmethod
    def generate_verification_code():
        digits = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]
        return "".join([random.choice(digits) for i in range(0, 6)])


class BillingAccount(models.Model):
    BUSINESS = "b"
    PERSONAL = "p"
    ACCOUNT_TYPE_CHOICES = [
        (BUSINESS, "Business"),
        (PERSONAL, "personal"),
    ]

    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    type = models.CharField(
        max_length=1,
        choices=ACCOUNT_TYPE_CHOICES,
    )
    account_name = models.CharField(max_length=100, null=True)
