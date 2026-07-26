from django.core.management.base import BaseCommand

from analyses.models import Analyse
from analyses.views import extract_species_to_remove_from_path


class Command(BaseCommand):
    help = "Convert stored analysis results_json to compact species delta mode"

    def handle(self, *args, **options):
        converted = 0
        skipped = 0

        for analyse in Analyse.objects.all().only("id", "life_list_file", "results_json"):
            current = analyse.results_json or {}
            if current.get("result_mode") == "species_delta_v1":
                skipped += 1
                continue

            species_to_remove = extract_species_to_remove_from_path(analyse.life_list_file.path)
            analyse.results_json = {
                "result_mode": "species_delta_v1",
                "species_to_remove": sorted(species_to_remove),
                "lifelist_count": len(species_to_remove),
            }
            analyse.save(update_fields=["results_json"])
            converted += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Converted: {converted}, already compact: {skipped}"
            )
        )
