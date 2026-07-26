from django.conf import settings
from django.core.management.base import BaseCommand

from analyses.models import BaselineAnalysis
from analyses.views import apply_country_aliases, save_baseline_to_file
from core.world_blanks import compute_baseline_results

import os


class Command(BaseCommand):
    help = "Rebuild the global baseline analysis from Especes_cibles_monde_copie.xlsx"

    def handle(self, *args, **options):
        target_species_path = os.path.join(
            settings.BASE_DIR,
            "core",
            "Especes_cibles_monde_copie.xlsx",
        )

        baseline, _ = BaselineAnalysis.objects.get_or_create(name="world_baseline")
        baseline.baseline_json = apply_country_aliases(
            compute_baseline_results(target_species_path)
        )
        baseline.save(update_fields=["baseline_json"])
        save_baseline_to_file(baseline.baseline_json)

        self.stdout.write(self.style.SUCCESS("Baseline rebuilt successfully (DB + file)."))
