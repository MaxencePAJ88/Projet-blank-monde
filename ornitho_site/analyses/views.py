from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import Analyse
from core.world_blanks import analyser_world_blanks
import os
import json


def upload_life_list_view(request):
    if request.method == "POST":
        fichier = request.FILES.get("life_list")
        if not fichier:
            return render(request, "analyses/upload.html", {"error": "Aucun fichier fourni."})

        analyse = Analyse.objects.create(
            life_list_file=fichier,
            titre="Analyse anonyme",
        )

        return redirect("analyses:detail", analyse_id=analyse.id)

    return render(request, "analyses/upload.html")


def detail_analyse_view(request, analyse_id):
    analyse = get_object_or_404(Analyse, pk=analyse_id)

    # 1. Récupérer les chemins des fichiers
    life_list_path = analyse.life_list_file.path
    target_species_path = os.path.join(
        settings.BASE_DIR,
        "core",
        "Especes_cibles_monde_copie.xlsx",
    )

    # 2. Lancer l'analyse complète
    resultats = analyser_world_blanks(life_list_path, target_species_path)

    liste_blanks_df = resultats["liste_blanks"]
    liste_pays_df = resultats["liste_pays"]
    continents_df = resultats["continents"]
    blancks_par_pays = resultats["blancks_par_pays"]

    # 🔧 Renommer colonnes globales
    liste_blanks_df = liste_blanks_df.rename(columns={
        "Country Count": "Country_Count",
        "Above Threshold Count": "Above_Threshold_Count",
        "Max Percentage": "Max_Percentage",
        "Max Percentage Country": "Max_Percentage_Country",
    })

    liste_pays_df = liste_pays_df.rename(columns={
        "Total Species": "Total_Species",
        "Species Above 0.0009": "Species_Above_00009",
        "Max Species Count": "Max_Species_Count",
    })

    continents_df = continents_df.rename(columns={
        "Total Species": "Total_Species",
        "Unique Species": "Unique_Species",
    })

    # 🔢 Convertir Max_Percentage en %
    if "Max_Percentage" in liste_blanks_df.columns:
        liste_blanks_df["Max_Percentage"] = (
            liste_blanks_df["Max_Percentage"] * 100
        ).round(4)

    # 🔢 Convertir les valeurs blancks_par_pays en %
    for country, rows in blancks_par_pays.items():
        for row in rows:
            row["value"] = round(row["value"] * 100, 4)



    # 🔽 Colonnes globales (non pays)
    global_cols = [
        "Species",
        "Country_Count",
        "Above_Threshold_Count",
        "Max_Percentage",
        "Max_Percentage_Country",
        "Median_Percentage",
    ]
    blanks_country_cols = [
        c for c in liste_blanks_df.columns
        if c not in global_cols
]
    # 🔢 Convertir toutes les colonnes-pays en pourcentage (x100)
    for col in blanks_country_cols:
        liste_blanks_df[col] = (liste_blanks_df[col] * 100).round(4)

    # 🔽 Colonnes pays (toutes les autres)
    blanks_country_cols = [
        c for c in liste_blanks_df.columns
        if c not in global_cols
    ]

    # 🔽 Données complètes pour le JS
    blanks_data_records = liste_blanks_df.to_dict(orient="records")

    # 🔽 TRI PAR DÉFAUT

    liste_blanks_df = liste_blanks_df.sort_values(
        by="Country_Count",
        ascending=False
    )

    liste_pays_df = liste_pays_df.sort_values(
        by="Total_Species",
        ascending=False
    )
    species_min = int(liste_pays_df["Total_Species"].min())
    species_max = int(liste_pays_df["Total_Species"].max())

    # Après le tri de liste_pays_df, par ex. juste après liste_pays_df = ...
    country_continents = {}
    for _, row in liste_pays_df.iterrows():
        country = row["Country"]
        continent = row["Continent"]
        country_continents[country] = continent




# Construire un dict {pays: {Total_Species: ..., Species_Above_00009: ..., ...}}
    # juste avant la boucle
    country_aliases = {
        # à adapter au fur et à mesure
        "United States": "United States of America",
        "Russia": "Russian Federation",
        "Côte d'Ivoire": "Ivory Coast",
        "Bolivia": "Bolivia (Plurinational State of)",
        "Venezuela": "Venezuela (Bolivarian Republic of)",
        "Iran": "Iran (Islamic Republic of)",
        "Syria": "Syrian Arab Republic",
        "Vietnam": "Viet Nam",
        # etc. tu complèteras selon les pays qui restent blancs
    }
    pays_stats = {}
    for _, row in liste_pays_df.iterrows():
        country = row["Country"]
        pays_stats[country] = {
            "Total_Species": int(row["Total_Species"]),
            "Species_Above_00009": int(row["Species_Above_00009"]),
            "Max_Species_Count": int(row["Max_Species_Count"]),
        }

    # 🔁 Alias : nom dans le GeoJSON -> nom dans ton Excel
    country_aliases = {
        "United Republic of Tanzania": "Tanzania",
        "Democratic Republic of the Congo": "Congo, Dem. Rep.",
        "Republic of the Congo": "DR Congo.",
        "Russia": "Russian Federation",
        "The Bahamas": "Bahamas",
        "Bolivia": "Bolivia",
        "Venezuela": "Venezuela",
        "Ivory Coast": "Cote d'Ivoire",
        "eSwatini": "Swaziland",
        "Palestine": "Palestinian Territory",
        "Vietnam": "Viet Nam",
        "Iran": "Iran (Islamic Republic of)",
        "Syria": "Syrian Arab Republic",
        "Czechia": "Czech Republic",
        "New Caledonia": "New Caledonia",
        "United States of America" : "United States",
        # ceux-ci sont peut-être absents de ton Excel :
        # "Western Sahara": "Western Sahara",
        "Greenland" : "Greenland",
        # "Puerto Rico": "Puerto Rico",
        "French Southern and Antarctic Lands": "French Southern and Antarctic Lands",
        "Antarctica": "Antarctica",
        "eSwatini" : "Eswatini",
        # "Northern Cyprus": "...",
        # "Somaliland": "...",
        "Republic of Serbia": "Serbia",
    }

    # On duplique les stats : pour chaque nom ADMIN, on copie les valeurs du nom Excel
    for admin_name, excel_name in country_aliases.items():
        if excel_name in pays_stats:
            pays_stats[admin_name] = pays_stats[excel_name]
            blancks_par_pays[admin_name] = blancks_par_pays[excel_name]
            country_continents[admin_name] = country_continents[excel_name]
    continents_df = continents_df.sort_values(
        by="Total_Species",
        ascending=False
    )
    pays_list = sorted(blancks_par_pays.keys())
    # CONTEXTE FINAL
    context = {
        "analyse": analyse,
        "liste_blanks": liste_blanks_df.to_dict(orient="records"),
        "liste_pays": liste_pays_df.to_dict(orient="records"),
        "continents": continents_df.to_dict(orient="records"),
        "pays_list": sorted(blancks_par_pays.keys()),
        "blancks_par_pays_json": json.dumps(blancks_par_pays),
        "blanks_country_cols": blanks_country_cols,
        "blanks_data_json": json.dumps(blanks_data_records),
        "pays_stats_json": json.dumps(pays_stats),
        "country_continents_json": json.dumps(country_continents),
        "species_min": species_min,
        "species_max": species_max,
    }

    return render(request, "analyses/detail.html", context)