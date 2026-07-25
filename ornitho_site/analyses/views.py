from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import reverse
from .models import Analyse, BaselineAnalysis
from core.world_blanks import (
    compute_baseline_results,
    filter_upload_results,
)
import csv
import io
import os


COUNTRY_ALIASES = {
    "United Republic of Tanzania": "Tanzania",
    "Democratic Republic of the Congo": "Congo, Dem. Rep.",
    "Republic of the Congo": "DR Congo.",
    "Russia": "Russian Federation",
    "The Bahamas": "Bahamas",
    "Bolivia": "Bolivia",
    "Venezuela": "Venezuela",
    "Ivory Coast": "Cote d'Ivoire",
    "eSwatini": "Eswatini",
    "Palestine": "Palestinian Territory",
    "Vietnam": "Viet Nam",
    "Iran": "Iran (Islamic Republic of)",
    "Syria": "Syrian Arab Republic",
    "Czechia": "Czech Republic",
    "New Caledonia": "New Caledonia",
    "United States of America": "United States",
    "Greenland": "Greenland",
    "French Southern and Antarctic Lands": "French Southern and Antarctic Lands",
    "Antarctica": "Antarctica",
    "Republic of Serbia": "Serbia",
}


def get_target_species_path():
    return os.path.join(
        settings.BASE_DIR,
        "core",
        "Especes_cibles_monde_copie.xlsx",
    )


def apply_country_aliases(results):
    pays_stats = results.get("pays_stats", {})
    blancks_par_pays = results.get("blancks_par_pays", {})
    country_continents = results.get("country_continents", {})

    for admin_name, excel_name in COUNTRY_ALIASES.items():
        if excel_name in pays_stats:
            pays_stats[admin_name] = pays_stats[excel_name]
            blancks_par_pays[admin_name] = blancks_par_pays.get(excel_name, [])
            country_continents[admin_name] = country_continents.get(excel_name)

    return results


def get_baseline_results(target_species_path):
    baseline, _ = BaselineAnalysis.objects.get_or_create(name="world_baseline")
    if not baseline.baseline_json:
        baseline.baseline_json = apply_country_aliases(
            compute_baseline_results(target_species_path)
        )
        baseline.save(update_fields=["baseline_json"])
    return baseline.baseline_json


def compute_analysis_results(analyse):
    life_list_path = analyse.life_list_file.path
    target_species_path = get_target_species_path()

    results = get_baseline_results(target_species_path)
    species_to_remove = set()
    with open(life_list_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row.get("Countable") == "1":
                species_name = row.get("Common Name")
                if species_name:
                    species_to_remove.add(species_name.strip().lower())

    filtered_results = apply_country_aliases(
        filter_upload_results(results, species_to_remove)
    )
    filtered_results["lifelist_count"] = len(species_to_remove)
    return filtered_results


def build_detail_context(request, analyse, results, is_baseline):
    if analyse:
        page_title = analyse.titre or f"Analyse #{analyse.id}"
        created_at = analyse.date_creation
        file_name = analyse.life_list_file.name
        blanks_endpoint_url = reverse("analyses:section_blanks_json", args=[analyse.id])
        blanks_by_country_endpoint_url = reverse("analyses:section_blanks_by_country_json", args=[analyse.id])
        summary_endpoint_url = reverse("analyses:section_summary_json", args=[analyse.id])
    else:
        page_title = "Baseline mondiale"
        created_at = None
        file_name = "Especes_cibles_monde_copie.xlsx"
        blanks_endpoint_url = reverse("analyses:baseline_section_blanks_json")
        blanks_by_country_endpoint_url = reverse("analyses:baseline_section_blanks_by_country_json")
        summary_endpoint_url = reverse("analyses:baseline_section_summary_json")

    return {
        "analyse": analyse,
        "is_baseline": is_baseline,
        "page_title": page_title,
        "file_name": file_name,
        "created_at": created_at,
        "lifelist_count": results.get("lifelist_count", 0 if is_baseline else None),
        "pays_list": results.get("pays_list", []),
        "blanks_endpoint_url": blanks_endpoint_url,
        "blanks_by_country_endpoint_url": blanks_by_country_endpoint_url,
        "summary_endpoint_url": summary_endpoint_url,
    }


def home_view(request):
    analyse = None
    results = None
    analyse_id = request.GET.get("analysis")

    if analyse_id and analyse_id.isdigit():
        analyse = Analyse.objects.filter(pk=int(analyse_id)).first()
        if analyse is not None:
            results = get_cached_analysis_results(analyse)

    if results is None:
        results = get_baseline_results(get_target_species_path())

    context = build_detail_context(
        request=request,
        analyse=analyse,
        results=results,
        is_baseline=(analyse is None),
    )
    return render(request, "analyses/detail.html", context)


def get_cached_analysis_results(analyse):
    if not analyse.results_json:
        analyse.results_json = compute_analysis_results(analyse)
        analyse.save(update_fields=["results_json"])
    return analyse.results_json


def upload_life_list_view(request):
    if request.method == "POST":
        fichier = request.FILES.get("life_list")
        if not fichier:
            return render(request, "analyses/upload.html", {"error": "Aucun fichier fourni."})

        titre = fichier.name or "Analyse"
        analyse = Analyse.objects.create(
            user=request.user if request.user.is_authenticated else None,
            life_list_file=fichier,
            titre=titre,
        )

        target_species_path = get_target_species_path()
        baseline_results = get_baseline_results(target_species_path)

        fichier.seek(0)
        text_stream = io.TextIOWrapper(fichier, encoding="utf-8", newline="")
        reader = csv.DictReader(text_stream)
        species_to_remove = {
            row.get("Common Name").strip().lower()
            for row in reader
            if row.get("Countable") == "1" and row.get("Common Name")
        }
        text_stream.detach()

        filtered_results = apply_country_aliases(
            filter_upload_results(baseline_results, species_to_remove)
        )
        filtered_results["lifelist_count"] = len(species_to_remove)
        analyse.results_json = filtered_results
        analyse.save(update_fields=["results_json"])

        return redirect(f"{reverse('analyses:home')}?analysis={analyse.id}")

    context = {}
    if request.user.is_authenticated:
        context["user_analyses"] = Analyse.objects.filter(user=request.user).order_by("-date_creation")
    return render(request, "analyses/upload.html", context)


def detail_analyse_view(request, analyse_id):
    return redirect(f"{reverse('analyses:home')}?analysis={analyse_id}")


@login_required
def refresh_baseline_view(request):
    if request.method != "POST":
        return redirect("analyses:home")

    target_species_path = get_target_species_path()
    baseline, _ = BaselineAnalysis.objects.get_or_create(name="world_baseline")
    baseline.baseline_json = apply_country_aliases(
        compute_baseline_results(target_species_path)
    )
    baseline.save(update_fields=["baseline_json"])
    return redirect("analyses:home")


@login_required
def user_analyses_view(request):
    analyses = Analyse.objects.filter(user=request.user).order_by("-date_creation")
    return render(request, "analyses/user_analyses.html", {
        "analyses": analyses,
    })


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("analyses:home")
    else:
        form = UserCreationForm()

    return render(request, "analyses/register.html", {"form": form})


def _section_blanks_json_from_results(results, request):

    search = (request.GET.get("search") or "").strip().lower()
    country = (request.GET.get("country") or "").strip()
    page = max(int(request.GET.get("page", 1)), 1)
    page_size = min(max(int(request.GET.get("page_size", 50)), 10), 200)
    threshold = 0.0000009

    filtered = []
    for row in results["liste_blanks_records"]:
        if search and search not in str(row.get("Species", "")).lower():
            continue
        if country:
            value = row.get(country)
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value <= threshold:
                continue
        filtered.append(row)

    filtered.sort(key=lambda row: (
        -int(row.get("Above_Threshold_Count", 0)),
        -int(row.get("Country_Count", 0)),
        -float(row.get("Max_Percentage", 0)),
        str(row.get("Species", "")).lower(),
    ))

    for idx, row in enumerate(filtered, start=1):
        row["_global_rank"] = idx

    total_count = len(filtered)
    start = (page - 1) * page_size
    page_data = filtered[start:start + page_size]

    payload = {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "blanks_data": page_data,
        "blanks_country_cols": results["blanks_country_cols"],
    }
    return JsonResponse(payload)


def section_blanks_json(request, analyse_id):
    analyse = get_object_or_404(Analyse, pk=analyse_id)
    results = get_cached_analysis_results(analyse)
    return _section_blanks_json_from_results(results, request)


def baseline_section_blanks_json(request):
    results = get_baseline_results(get_target_species_path())
    return _section_blanks_json_from_results(results, request)


def _section_blanks_by_country_json_from_results(results, request):

    country = (request.GET.get("country") or "").strip()
    if not country:
        return JsonResponse({"error": "Country parameter is required."}, status=400)

    blancks_par_pays = results.get("blancks_par_pays", {})
    country_rows = blancks_par_pays.get(country, [])

    blanks_data = results["liste_blanks_records"]
    sorted_by_rank = sorted(
        blanks_data,
        key=lambda row: (
            -int(row.get("Above_Threshold_Count", 0)),
            -int(row.get("Country_Count", 0)),
            -float(row.get("Max_Percentage", 0)),
            str(row.get("Species", "")).lower(),
        )
    )
    rank_by_species = {
        row.get("Species"): idx + 1
        for idx, row in enumerate(sorted_by_rank)
    }

    result_rows = [
        {
            "species": row.get("species"),
            "value": row.get("value"),
            "global_rank": rank_by_species.get(row.get("species")),
        }
        for row in country_rows
    ]

    result_rows.sort(key=lambda row: ((row["global_rank"] or 999999), str(row["species"] or "").lower()))

    return JsonResponse({
        "country": country,
        "rows": result_rows,
        "total_count": len(result_rows),
    })


def section_blanks_by_country_json(request, analyse_id):
    analyse = get_object_or_404(Analyse, pk=analyse_id)
    results = get_cached_analysis_results(analyse)
    return _section_blanks_by_country_json_from_results(results, request)


def baseline_section_blanks_by_country_json(request):
    results = get_baseline_results(get_target_species_path())
    return _section_blanks_by_country_json_from_results(results, request)


def _section_summary_json_from_results(results):
    payload = {
        "liste_pays_records": results["liste_pays_records"],
        "continents_records": results["continents_records"],
        "pays_stats": results["pays_stats"],
        "country_continents": results["country_continents"],
        "species_min": results["species_min"],
        "species_max": results["species_max"],
    }
    return JsonResponse(payload)


def section_summary_json(request, analyse_id):
    analyse = get_object_or_404(Analyse, pk=analyse_id)
    results = get_cached_analysis_results(analyse)
    return _section_summary_json_from_results(results)


def baseline_section_summary_json(request):
    results = get_baseline_results(get_target_species_path())
    return _section_summary_json_from_results(results)