#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 11 14:23:47 2025

Premiere fonction: build_user_target_species(life_list_file, target_species_file)
@author: mp
"""

# core/world_blanks.py
import pandas as pd


def build_user_target_species(life_list_file, target_species_file):
    """
    Prépare un fichier d'espèces cibles adapté à un utilisateur,
    en supprimant les espèces déjà observées dans sa life list.

    Parameters
    ----------
    life_list_file : str ou file-like
        Fichier CSV eBird "world life list" de l'utilisateur.
    target_species_file : str ou file-like
        Fichier Excel des espèces cibles "monde" (version de base).

    Returns
    -------
    updated_target_species_df : pd.DataFrame
        Version mise à jour du fichier espèces cibles, avec les espèces déjà cochées supprimées.
        La première ligne (header avec les espèces d'origine) est conservée.
    dv_df : pd.DataFrame
        Même tableau mais sans la première ligne (utile pour tes validations DV).
    """

    # Charger la life list (observations) de l'utilisateur
    life_list_df = pd.read_csv(life_list_file)

    # Charger le fichier des espèces cibles (sans en-tête, comme dans ton script)
    target_species_df = pd.read_excel(target_species_file, dtype=str, header=None)

    # Sauvegarder la première ligne (contenant les espèces)
    species_header = target_species_df.iloc[0].copy()

    # Filtrer les espèces observées selon tes critères
    # Ici tu avais: (life_list_df["Countable"] == 1)
    # Si tu veux remettre "Exotic != 'N'" plus tard, on pourra le rajouter.
    filtered_life_list = life_list_df[
        (life_list_df["Countable"] == 1)
    ]

    # Extraire la liste des espèces à retirer du fichier cibles (par "Common Name")
    species_to_remove = set(filtered_life_list["Common Name"])

    # Copie du fichier espèces cibles pour modification
    updated_target_species_df = target_species_df.copy()

    # Parcours des colonnes par paires (Nom d'espèce, Valeur associée)
    columns = list(updated_target_species_df.columns)
    for i in range(0, len(columns) - 1, 2):
        col_species = columns[i]
        col_value = columns[i + 1]

        # Suppression des espèces déjà vues + leurs valeurs
        for index, value in updated_target_species_df[col_species].items():
            if isinstance(value, str) and value in species_to_remove:
                updated_target_species_df.at[index, col_species] = None
                updated_target_species_df.at[index, col_value] = None

        # Réorganisation des colonnes pour "tasser" les lignes non vides en haut
        non_empty_species = updated_target_species_df[col_species].dropna().values.tolist()
        non_empty_values = updated_target_species_df[col_value].dropna().values.tolist()

        # Alignement des longueurs pour éviter les erreurs
        min_length = min(len(non_empty_species), len(non_empty_values))
        non_empty_species = non_empty_species[:min_length]
        non_empty_values = non_empty_values[:min_length]

        # Remplir la colonne avec les valeurs non vides puis des None
        updated_target_species_df[col_species] = pd.Series(
            non_empty_species + [None] * (len(updated_target_species_df) - len(non_empty_species))
        )
        updated_target_species_df[col_value] = pd.Series(
            non_empty_values + [None] * (len(updated_target_species_df) - len(non_empty_values))
        )

    # dv_df = copie complète, pas de suppression
    dv_df = updated_target_species_df.copy()

    return updated_target_species_df, dv_df



def compute_liste_blanks_world_classified(dv_df: pd.DataFrame, threshold: float = 0.0009) -> pd.DataFrame:
    """
    À partir du DataFrame 'DV' (équivalent de Especes_cibles_monde_DV.xlsx),
    construit le tableau 'Liste_blancks_world_classified' avec, pour chaque espèce :

      - le nombre de pays où elle apparaît,
      - le nombre de pays où elle dépasse un certain seuil,
      - le pourcentage max et le pays associé,
      - la médiane des pourcentages > seuil,
      - les valeurs par pays (une colonne par pays).

    Parameters
    ----------
    dv_df : pd.DataFrame
        DataFrame sans en-tête, dont :
          - la première ligne contient les noms de pays,
          - puis les lignes suivantes contiennent les espèces (colonne i) et valeurs (colonne i+1).
    threshold : float
        Seuil utilisé pour "Above Threshold Count" et la liste des pourcentages au-dessus du seuil.

    Returns
    -------
    final_df : pd.DataFrame
        Tableau final avec colonnes :
          ["Species", "Country Count", "Above Threshold Count",
           "Max Percentage", "Max Percentage Country", "Median Percentage"]
        + une colonne par pays.
    """

    # On travaille sur une copie pour ne pas modifier dv_df en place
    data = dv_df.copy()

    species_dict = {}   # {species: {...}}
    countries = []      # liste des pays (ordre des colonnes)

    # Parcourir les colonnes deux par deux : (espèce, valeur) pour un pays
    for i in range(0, data.shape[1], 2):
        country = data.iloc[0, i]

        if pd.isna(country):
            # colonne vide -> on ignore
            continue

        countries.append(country)

        # Colonne i = espèces (à partir de la ligne 1)
        species_column = data.iloc[1:, i]
        # Colonne i+1 = valeurs (pourcentage) -> conversion numérique
        values_column = pd.to_numeric(data.iloc[1:, i + 1], errors="coerce")

        # Ajouter les espèces et leurs pourcentages dans le dict
        for species, value in zip(species_column, values_column):
            if pd.isna(species) or pd.isna(value):
                continue

            if species not in species_dict:
                species_dict[species] = {
                    "countries": {},                  # {country: value}
                    "count": 0,                       # nb de pays
                    "above_threshold_count": 0,       # nb de pays > seuil
                    "max_percentage": 0,
                    "max_percentage_country": None,
                    "above_threshold_percentages": [] # liste des valeurs > seuil
                }

            sp_info = species_dict[species]

            # Si on n'a pas encore ce pays pour cette espèce, on incrémente le count
            if country not in sp_info["countries"]:
                sp_info["countries"][country] = 0
                sp_info["count"] += 1

            # Enregistrer la valeur pour ce pays
            sp_info["countries"][country] = value

            # Mettre à jour les métriques
            if value > threshold:
                sp_info["above_threshold_count"] += 1
                sp_info["above_threshold_percentages"].append(value)

            if value > sp_info["max_percentage"]:
                sp_info["max_percentage"] = value
                sp_info["max_percentage_country"] = country

    # Construire le DataFrame final
    columns = [
        "Species",
        "Country Count",
        "Above Threshold Count",
        "Max Percentage",
        "Max Percentage Country",
        "Median Percentage",
    ] + countries

    rows = []

    for species, info in species_dict.items():
        median_above_threshold = (
            pd.Series(info["above_threshold_percentages"]).median()
            if info["above_threshold_percentages"] else 0
        )

        row = [
            species,
            info["count"],
            info["above_threshold_count"],
            info["max_percentage"],
            info["max_percentage_country"],
            median_above_threshold,
        ]

        # Ajouter les valeurs pour chaque pays dans l'ordre défini par 'countries'
        for country in countries:
            row.append(info["countries"].get(country, 0))

        rows.append(row)

    final_df = pd.DataFrame(rows, columns=columns)
    return final_df


def compute_liste_pays_with_nb_coches(dv_df: pd.DataFrame, threshold: float = 0.0009) -> pd.DataFrame:
    """
    À partir du DataFrame 'DV' (équivalent de Especes_cibles_monde_DV.xlsx),
    calcule pour chaque pays :

      - son continent,
      - le nombre total d'espèces (non vides),
      - le nombre d'espèces dont la valeur > threshold,
      - le nombre d'espèces pour lesquelles ce pays a la valeur max.

    Structure attendue de dv_df :
      - première ligne : pour chaque paire de colonnes (2 par pays),
          * colonne i   : nom du pays
          * colonne i+1 : continent
      - lignes suivantes :
          * colonne i   : nom de l'espèce
          * colonne i+1 : valeur (pourcentage) pour ce pays

    Parameters
    ----------
    dv_df : pd.DataFrame
        DataFrame de base, sans header, correspondant à l'ancien fichier DV.
    threshold : float
        Seuil pour compter 'Species Above threshold'.

    Returns
    -------
    final_results_df : pd.DataFrame
        Colonnes :
          ["Country", "Continent", "Total Species", "Species Above threshold", "Max Species Count"]
    """

    data = dv_df.copy()

    results = []      # liste des [country, continent, total_species, species_above_threshold]
    species_dict = {} # pour chaque espèce : pays où elle a la valeur max

    # Parcourir les colonnes deux par deux
    for i in range(0, data.shape[1], 2):
        country = data.iloc[0, i]
        continent = data.iloc[0, i + 1] if i + 1 < data.shape[1] else None

        # Ignorer les colonnes vides
        if pd.isna(country) or pd.isna(continent):
            continue

        # Colonne des espèces (à partir de la ligne 1)
        species_column = data.iloc[1:, i]
        # Colonne des valeurs (à partir de la ligne 1)
        values_column = pd.to_numeric(data.iloc[1:, i + 1], errors="coerce")

        # Nombre total d'espèces (non vides) pour ce pays
        total_species = species_column.dropna().count()

        # Nombre d'espèces > threshold
        species_above_threshold = values_column[values_column > threshold].count()

        # Mise à jour du dictionnaire des espèces
        for species, value in zip(species_column, values_column):
            if pd.isna(species) or pd.isna(value):
                continue

            if species not in species_dict:
                # Première fois qu'on voit cette espèce
                species_dict[species] = {"value": value, "country": country}
            else:
                # Si on trouve une valeur plus grande pour cette espèce, on met à jour le pays max
                if value > species_dict[species]["value"]:
                    species_dict[species] = {"value": value, "country": country}

        # Ajouter les résultats pour ce pays
        results.append([country, continent, total_species, species_above_threshold])

    # Compter le nombre d'espèces pour lesquelles chaque pays détient la valeur maximale
    country_counts = {}
    for info in species_dict.values():
        max_country = info["country"]
        if max_country not in country_counts:
            country_counts[max_country] = 0
        country_counts[max_country] += 1

    # Construire les résultats finaux
    final_results = []
    for country, continent, total_species, species_above_threshold in results:
        max_species_count = country_counts.get(country, 0)
        final_results.append(
            [country, continent, total_species, species_above_threshold, max_species_count]
        )

    final_results_df = pd.DataFrame(
        final_results,
        columns=[
            "Country",
            "Continent",
            f"Total Species",
            f"Species Above {threshold}",
            "Max Species Count",
        ],
    )

    return final_results_df


def compute_blancks_important_by_countries(dv_df: pd.DataFrame):
    """
    À partir du DataFrame 'DV' (équivalent de Especes_cibles_monde_DV.xlsx),
    construit :

      1) un DataFrame structuré comme l'ancien fichier 'Blancks_important_by_countries.xlsx',
         avec 2 colonnes par pays :
           - col i   : [Country, Continent, Species1, Species2, ...]
           - col i+1 : [MaxSpeciesCount, "", Value1, Value2, ...]

      2) un dictionnaire prêt pour le site web :
         {
           "Afghanistan": [
               {"species": "Pied Bushchat", "value": 0.1504},
               {"species": "Citrine Wagtail", "value": 0.1038},
               ...
           ],
           "Albania": [...],
           ...
         }

    Parameters
    ----------
    dv_df : pd.DataFrame
        DataFrame de base, sans header, correspondant à l'ancien fichier DV.

    Returns
    -------
    blancks_df : pd.DataFrame
        Tableau final au format "Excel" (2 colonnes par pays).
    blancks_dict : dict
        Dictionnaire {country: [ {species, value}, ... ]} trié par valeur décroissante.
    """

    data = dv_df.copy()

    # 1) Construire species_dict = pour chaque espèce, le pays où sa valeur est max
    species_dict = {}

    for i in range(0, data.shape[1], 2):
        country = data.iloc[0, i]
        continent = data.iloc[0, i + 1] if i + 1 < data.shape[1] else None

        if pd.isna(country) or pd.isna(continent):
            continue

        species_column = data.iloc[1:, i]
        values_column = pd.to_numeric(data.iloc[1:, i + 1], errors="coerce")

        for species, value in zip(species_column, values_column):
            if pd.isna(species) or pd.isna(value):
                continue

            if species not in species_dict:
                species_dict[species] = {"value": value, "country": country}
            else:
                if value > species_dict[species]["value"]:
                    species_dict[species] = {"value": value, "country": country}

    # 2) Liste des pays et continents à partir de la première ligne
    countries = data.iloc[0, ::2].dropna().tolist()
    continents = data.iloc[0, 1::2].dropna().tolist()
    country_species_counts = {country: 0 for country in countries}

    # 3) Compter le nombre d'espèces pour lesquelles chaque pays a la valeur max
    for info in species_dict.values():
        max_country = info["country"]
        if max_country in country_species_counts:
            country_species_counts[max_country] += 1

    # 4) Construire la structure finale à 2 colonnes par pays
    corrected_sorted_data = []
    blancks_dict = {}  # <- pour le site web : {country: [ {species, value}, ... ]}

    for country, continent in zip(countries, continents):
        if country not in country_species_counts:
            continue

        # Espèces pour lesquelles ce pays est le max
        species_in_country = [
            (species, info["value"])
            for species, info in species_dict.items()
            if info["country"] == country
        ]

        # Tri décroissant par valeur
        sorted_species_values = sorted(
            species_in_country, key=lambda x: x[1], reverse=True
        )

        # --- Structure pour le site web ---
        blancks_dict[country] = [
            {"species": species, "value": value}
            for species, value in sorted_species_values
        ]

        # --- Structure "Excel" (2 colonnes par pays) ---
        # Colonne 1 : Country, Continent, Species...
        country_column = [country, continent]
        # Colonne 2 : MaxSpeciesCount, "", Values...
        values_column = [country_species_counts[country], ""]

        for species, value in sorted_species_values:
            country_column.append(species)
            values_column.append(value)

        corrected_sorted_data.append(country_column)
        corrected_sorted_data.append(values_column)

    # 5) Transposer pour obtenir un tableau tabulaire
    blancks_df = pd.DataFrame(corrected_sorted_data).T

    # 6) Vérifier/ajuster les totaux d'espèces pour chaque pays
    for i in range(0, blancks_df.shape[1], 2):
        header_value = blancks_df.iloc[0, i + 1]
        species_count = blancks_df.iloc[2:, i].count()
        if header_value != species_count:
            blancks_df.iloc[0, i + 1] = species_count

    return blancks_df, blancks_dict


def compute_continents_species_numbers(dv_df: pd.DataFrame) -> pd.DataFrame:
    """
    À partir du DataFrame 'DV' (équivalent de Especes_cibles_monde_DV.xlsx),
    calcule, pour chaque continent :

      - le nombre total d'espèces présentes,
      - le nombre d'espèces uniques (présentes uniquement dans ce continent).

    Structure attendue de dv_df :
      - ligne 0 : [Country, Continent, Country, Continent, ...]
      - lignes suivantes : pour chaque paire de colonnes (i, i+1) :
          * col i   : nom de l'espèce
          * col i+1 : valeur (non utilisée ici, seule la présence compte)

    Parameters
    ----------
    dv_df : pd.DataFrame
        DataFrame de base.

    Returns
    -------
    results_df : pd.DataFrame
        Colonnes : ["Continent", "Total Species", "Unique Species"]
    """

    data = dv_df.copy()

    continent_species = {}  # {continent: set(species)}
    global_species = {}     # {species: set(continents)}

    # Parcourir les colonnes deux par deux
    for i in range(0, data.shape[1], 2):
        country = data.iloc[0, i]
        continent = data.iloc[0, i + 1] if i + 1 < data.shape[1] else None

        if pd.isna(country) or pd.isna(continent):
            continue

        species_column = data.iloc[1:, i]

        # Initialiser l'entrée pour ce continent si nécessaire
        if continent not in continent_species:
            continent_species[continent] = set()

        # Ajouter les espèces à ce continent et au suivi global
        for species in species_column.dropna():
            continent_species[continent].add(species)

            if species not in global_species:
                global_species[species] = set()
            global_species[species].add(continent)

    # Calcul des métriques finales
    results = []
    for continent, species_set in continent_species.items():
        total_species = len(species_set)
        unique_species = sum(
            1 for species in species_set if len(global_species[species]) == 1
        )
        results.append([continent, total_species, unique_species])

    results_df = pd.DataFrame(
        results, columns=["Continent", "Total Species", "Unique Species"]
    ).sort_values("Continent").reset_index(drop=True)

    return results_df


def analyser_world_blanks(life_list_file, target_species_file):
    """
    Point d'entrée unique pour analyser une life list eBird "monde".

    Parameters
    ----------
    life_list_file : str ou file-like
        CSV eBird de l'utilisateur.
    target_species_file : str ou file-like
        Fichier Excel des espèces cibles monde (version de base).

    Returns
    -------
    resultats : dict
        {
          "updated_targets": DataFrame,
          "dv": DataFrame,
          "liste_blanks": DataFrame,
          "liste_pays": DataFrame,
          "blancks_df": DataFrame,
          "blancks_par_pays": dict,
          "continents": DataFrame,
        }
    """

    # 1. Adapter les espèces cibles à l'utilisateur
    updated_df, dv_df = build_user_target_species(life_list_file, target_species_file)

    # 2. Blanks par espèce
    liste_blanks_df = compute_liste_blanks_world_classified(dv_df)

    # 3. Stats par pays
    liste_pays_df = compute_liste_pays_with_nb_coches(dv_df)

    # 4. Blanks importants par pays (table + dict pour le site)
    blancks_df, blancks_dict = compute_blancks_important_by_countries(dv_df)

    # 5. Stats par continents
    continents_df = compute_continents_species_numbers(dv_df)

    return {
        "updated_targets": updated_df,
        "dv": dv_df,
        "liste_blanks": liste_blanks_df,
        "liste_pays": liste_pays_df,
        "blancks_df": blancks_df,
        "blancks_par_pays": blancks_dict,
        "continents": continents_df,
    }




if __name__ == "__main__":
    import os

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    life_list_path = os.path.join(SCRIPT_DIR, "ebird_world_life_list_paul.csv")
    target_species_path = os.path.join(SCRIPT_DIR, "Especes_cibles_monde_copie.xlsx")

    resultats = analyser_world_blanks(life_list_path, target_species_path)

    print("\n✅ liste_blanks :", resultats["liste_blanks"].shape)
    print(resultats["liste_blanks"].head())

    print("\n✅ liste_pays :", resultats["liste_pays"].shape)
    print(resultats["liste_pays"].head())

    print("\n✅ continents :")
    print(resultats["continents"])










