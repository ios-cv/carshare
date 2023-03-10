# Generated by Django 4.1.4 on 2023-01-04 20:22

from django.db import migrations, models
import drivers.models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0003_alter_fulldriverprofile_dvla_summary_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="fulldriverprofile",
            name="approved_licence_place_of_issue",
        ),
        migrations.RemoveField(
            model_name="fulldriverprofile",
            name="licence_place_of_issue",
        ),
        migrations.AddField(
            model_name="fulldriverprofile",
            name="approved_proof_of_address",
            field=models.BooleanField(
                blank=True,
                choices=[(True, "Approve"), (False, "Reject"), ("", "Unchecked")],
                default="",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="fulldriverprofile",
            name="proof_of_address",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=drivers.models.proof_of_address_upload_to,
            ),
        ),
    ]
