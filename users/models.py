from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


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
