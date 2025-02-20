# Generated by Django 5.0.11 on 2025-02-20 12:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hardware", "0009_telemetry"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="telemetry",
            index=models.Index(
                fields=["box_id", "-created_at"], name="idx_box_created_desc"
            ),
        ),
        migrations.AddIndex(
            model_name="telemetry",
            index=models.Index(
                condition=models.Q(("soc_percent__isnull", False)),
                fields=["box_id", "-created_at"],
                name="idx_created_desc_soc_not_null",
            ),
        ),
        migrations.AlterModelTable(
            name="telemetry",
            table=None,
        ),
    ]
