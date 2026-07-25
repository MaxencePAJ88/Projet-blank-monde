from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analyses", "0002_analyse_results_json"),
    ]

    operations = [
        migrations.CreateModel(
            name="BaselineAnalysis",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        default="world_baseline",
                        max_length=200,
                        unique=True,
                    ),
                ),
                (
                    "baseline_json",
                    models.JSONField(blank=True, null=True),
                ),
                (
                    "date_creation",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "date_updated",
                    models.DateTimeField(auto_now=True),
                ),
            ],
        ),
    ]
