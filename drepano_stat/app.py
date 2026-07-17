"""Interface Streamlit de DrepanoStat."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.descriptive import make_descriptive_table, make_efficiency_ranking, make_group_ranking
from src.display_labels import apply_display_labels, display_label, internal_label
from src.export import generate_results_zip
from src.plots import (
    plot_efficiency_ranking,
    plot_group_dilution_heatmap,
    plot_or_vs_vehicle,
    plot_prop_drepano_by_condition,
    plot_prop_normal_by_condition,
    save_figure_to_bytes,
)
from src.preprocessing import preprocess_data
from src.report import generate_word_report
from src.statistics import run_glm_vs_vehicle, run_pairwise_group_comparisons
from src.template_generator import DEFAULT_DILUTIONS, generate_excel_template
from src.utils import format_table_for_display, slugify
from src.validation import validate_input_file


def parse_items(raw_value: str) -> list[str]:
    values = [item.strip() for item in raw_value.splitlines() if item.strip()]
    return list(dict.fromkeys(values))


def csv_bytes(dataframe) -> bytes:
    """Exporte une copie avec libellés français, en conservant les nombres bruts."""
    return apply_display_labels(dataframe).to_csv(index=False).encode("utf-8-sig")


def show_table(dataframe) -> None:
    """Affiche une copie formatée ; les données sources ne sont jamais modifiées."""
    st.dataframe(format_table_for_display(dataframe), use_container_width=True, hide_index=True)


def display_figure_with_downloads(figure, file_stem: str, key_prefix: str) -> None:
    st.pyplot(figure, use_container_width=True)
    png_column, svg_column = st.columns(2)
    with png_column:
        st.download_button(
            "Télécharger en PNG (300 dpi)",
            data=save_figure_to_bytes(figure, format="png", dpi=300),
            file_name=f"{file_stem}.png",
            mime="image/png",
            key=f"{key_prefix}_png",
            use_container_width=True,
        )
    with svg_column:
        st.download_button(
            "Télécharger en SVG",
            data=save_figure_to_bytes(figure, format="svg", dpi=300),
            file_name=f"{file_stem}.svg",
            mime="image/svg+xml",
            key=f"{key_prefix}_svg",
            use_container_width=True,
        )


st.set_page_config(page_title="DrepanoStat", page_icon="🩸", layout="wide")

st.sidebar.title("DrepanoStat")
st.sidebar.caption("Analyse statistique des tests anti-falcémiants")
st.sidebar.markdown(
    """
**Étapes de l’analyse**

1. Définir l’étude
2. Importer le fichier rempli
3. Vérifier les données
4. Examiner les résultats descriptifs
5. Réaliser les comparaisons statistiques
6. Générer les graphes
7. Télécharger le rapport et l’archive
"""
)
progress_placeholder = st.sidebar.empty()
status_placeholder = st.sidebar.empty()

st.title("DrepanoStat — Analyse statistique des tests anti-falcémiants")
st.caption(
    "Application destinée à la préparation, au contrôle et à l’analyse de données "
    "expérimentales de comptage de globules rouges."
)

tabs = st.tabs(
    [
        "1. Définir l’étude",
        "2. Importer le fichier",
        "3. Vérification",
        "4. Résultats descriptifs",
        "5. Analyse statistique",
        "6. Graphes",
        "7. Rapport et ZIP",
    ]
)

with tabs[0]:
    st.header("Définir l’étude et générer le modèle Excel")
    st.info(
        "Définissez les conditions de l’expérience. DrepanoStat générera toutes les "
        "lignes attendues et laissera N et D à compléter."
    )
    first_column, second_column = st.columns(2)
    with first_column:
        study_name = st.text_input(
            "Nom de l’étude", placeholder="Test anti-falcémiant Combretum"
        )
        product_name = st.text_input(
            "Plante ou produit testé", placeholder="Combretum glutinosum"
        )
        groups_text = st.text_area(
            "Groupes d’extraits (un par ligne)",
            value="Fruit\nFeuille\nFruit+Feuille",
            height=120,
        )
    with second_column:
        dilutions = st.multiselect(
            "Dilutions utilisées", options=DEFAULT_DILUTIONS, default=DEFAULT_DILUTIONS
        )
        controls_text = st.text_area(
            "Témoins (un par ligne)",
            value="Témoin véhicule\nTémoin Emmel",
            height=90,
        )
        repetitions = st.number_input(
            "Nombre de répétitions par condition",
            min_value=1,
            max_value=100,
            value=3,
            step=1,
        )

    groups = parse_items(groups_text)
    controls = [internal_label(value) for value in parse_items(controls_text)]
    configuration_errors = []
    if not study_name.strip():
        configuration_errors.append("Renseignez le nom de l’étude.")
    if not product_name.strip():
        configuration_errors.append("Renseignez la plante ou le produit testé.")
    if not groups:
        configuration_errors.append("Ajoutez au moins un groupe d’extrait.")
    if not dilutions:
        configuration_errors.append("Sélectionnez au moins une dilution.")
    if not controls:
        configuration_errors.append("Ajoutez au moins un témoin.")
    if groups and controls and set(map(str.casefold, groups)) & set(map(str.casefold, controls)):
        configuration_errors.append("Un nom ne peut pas être à la fois groupe et témoin.")

    row_count = (len(groups) * len(dilutions) + len(controls)) * int(repetitions)
    st.metric("Lignes de saisie qui seront générées", row_count)
    if configuration_errors:
        for message in configuration_errors:
            st.warning(message)
    else:
        model_bytes = generate_excel_template(
            study_name=study_name,
            product_name=product_name,
            groups=groups,
            dilutions=dilutions,
            controls=controls,
            repetitions=int(repetitions),
        )
        st.download_button(
            "Télécharger le modèle Excel",
            data=model_bytes,
            file_name=f"drepano_modele_{slugify(study_name)}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

with tabs[1]:
    st.header("Importer le fichier rempli")
    st.info(
        "Renseignez N et D dans le modèle, enregistrez-le au format XLSX, puis importez-le ici."
    )
    uploaded_file = st.file_uploader(
        "Fichier DrepanoStat rempli",
        type=["xlsx"],
        help='Le classeur doit contenir la feuille "Données".',
    )

validated_data = None
blocking_errors: list[str] = []
validation_warnings: list[str] = []
if uploaded_file is not None:
    validated_data, blocking_errors, validation_warnings = validate_input_file(
        uploaded_file, expected_repetitions=int(repetitions)
    )

analysis_ready = uploaded_file is not None and not blocking_errors
preprocessed_data = descriptive_table = efficiency_ranking = group_ranking = None
glm_table = pairwise_table = None
glm_messages: list[str] = []
pairwise_warnings: list[str] = []
figures = {}

if analysis_ready:
    preprocessed_data = preprocess_data(validated_data)
    descriptive_table = make_descriptive_table(preprocessed_data)
    efficiency_ranking = make_efficiency_ranking(preprocessed_data)
    group_ranking = make_group_ranking(preprocessed_data)
    glm_table, glm_model, glm_messages = run_glm_vs_vehicle(preprocessed_data)
    pairwise_table, pairwise_warnings = run_pairwise_group_comparisons(preprocessed_data)

with tabs[2]:
    st.header("Vérification des données")
    st.caption("Les erreurs bloquantes empêchent l’analyse ; les avertissements sont informatifs.")
    if uploaded_file is None:
        st.info("Importez d’abord un fichier rempli dans l’onglet 2.")
    elif blocking_errors:
        st.error(f"{len(blocking_errors)} erreur(s) bloquante(s) détectée(s).")
        for message in blocking_errors:
            st.error(display_label(message))
    else:
        st.success("Le fichier est valide et peut être analysé.")
        for message in validation_warnings:
            st.warning(display_label(message))
        metric_columns = st.columns(5)
        metrics = [
            ("Lignes", len(validated_data)),
            ("Conditions", preprocessed_data["condition_standard"].nunique()),
            ("Groupes d’extraits", preprocessed_data.loc[preprocessed_data["type_condition"].eq("Extrait"), "groupe"].nunique()),
            ("Dilutions", preprocessed_data.loc[preprocessed_data["type_condition"].eq("Extrait"), "dilution"].nunique()),
            ("Témoins", preprocessed_data.loc[preprocessed_data["type_condition"].eq("Témoin"), "temoin"].nunique()),
        ]
        for column, (label, value) in zip(metric_columns, metrics, strict=True):
            column.metric(label, value)
        show_table(validated_data)

with tabs[3]:
    st.header("Résultats descriptifs")
    st.caption("Les proportions affichées sont des moyennes par répétition expérimentale.")
    if not analysis_ready:
        st.info("Un fichier valide est nécessaire pour afficher cette section.")
    else:
        best_columns = st.columns(2)
        best_condition = efficiency_ranking.iloc[0] if not efficiency_ranking.empty else None
        best_group = group_ranking.iloc[0] if not group_ranking.empty else None
        best_columns[0].metric(
            "Condition présentant la plus faible proportion observée",
            best_condition["condition_label"] if best_condition is not None else "—",
        )
        best_columns[1].metric(
            "Groupe présentant la plus faible proportion observée",
            best_group["groupe"] if best_group is not None else "—",
        )
        with st.expander("Afficher les données prétraitées"):
            show_table(preprocessed_data)
        st.subheader("Tableau descriptif par condition")
        show_table(descriptive_table)
        st.download_button(
            "Télécharger le tableau descriptif",
            csv_bytes(descriptive_table),
            f"drepano_descriptif_{slugify(study_name)}.csv",
            "text/csv",
        )
        st.subheader("Classement descriptif des conditions")
        show_table(efficiency_ranking)
        st.download_button(
            "Télécharger le classement",
            csv_bytes(efficiency_ranking),
            f"drepano_classement_{slugify(study_name)}.csv",
            "text/csv",
        )
        st.subheader("Classement descriptif des groupes")
        show_table(group_ranking)
        st.download_button(
            "Télécharger le classement des groupes",
            csv_bytes(group_ranking),
            f"drepano_classement_groupes_{slugify(study_name)}.csv",
            "text/csv",
        )

with tabs[4]:
    st.header("Analyse statistique")
    st.info("Le Témoin véhicule est utilisé comme référence pour comparer les extraits.")
    if not analysis_ready:
        st.info("Un fichier valide est nécessaire pour afficher cette section.")
    else:
        st.subheader("GLM binomial vs Témoin véhicule")
        st.caption(
            "Un OR > 1 indique une augmentation des chances d’observer des globules rouges "
            "normaux par rapport au Témoin véhicule."
        )
        for message in glm_messages:
            (st.error if message.startswith("Erreur") else st.warning)(display_label(message))
        if not glm_table.empty:
            show_table(glm_table)
            st.download_button(
                "Télécharger les OR vs Témoin véhicule",
                csv_bytes(glm_table),
                f"drepano_or_vs_temoin_vehicule_{slugify(study_name)}.csv",
                "text/csv",
            )
        st.subheader("Comparaisons entre groupes à dilution identique")
        st.caption(
            "Un OR > 1 favorise le premier groupe nommé dans la comparaison pour la réponse [N, D]."
        )
        for message in pairwise_warnings:
            st.warning(display_label(message))
        if not pairwise_table.empty:
            show_table(pairwise_table)
            st.download_button(
                "Télécharger les comparaisons entre groupes",
                csv_bytes(pairwise_table),
                f"drepano_comparaisons_groupes_{slugify(study_name)}.csv",
                "text/csv",
            )

if analysis_ready:
    descriptive_display = apply_display_labels(descriptive_table)
    efficiency_display = apply_display_labels(efficiency_ranking)
    glm_display = apply_display_labels(glm_table)
    figures = {
        "Proportion de drépanocytes par condition": plot_prop_drepano_by_condition(descriptive_display),
        "Proportion de globules rouges normaux par condition": plot_prop_normal_by_condition(descriptive_display),
        "Classement descriptif des conditions": plot_efficiency_ranking(efficiency_display),
    }
    if not glm_table.empty:
        figures["Odds ratios vs Témoin véhicule"] = plot_or_vs_vehicle(glm_display)
    extracts = descriptive_table.loc[descriptive_table["type_condition"].eq("Extrait")]
    if extracts["groupe"].nunique() > 1 and extracts["dilution"].nunique() > 1:
        figures["Heatmap groupe × dilution"] = plot_group_dilution_heatmap(descriptive_display)

with tabs[5]:
    st.header("Graphes automatiques")
    st.caption("Les exports PNG sont produits à 300 dpi ; le format SVG est vectoriel.")
    if not analysis_ready:
        st.info("Un fichier valide est nécessaire pour générer les figures.")
    else:
        graph_names = {
            "Proportion de drépanocytes par condition": "proportion_drepanocytes",
            "Proportion de globules rouges normaux par condition": "proportion_normaux",
            "Classement descriptif des conditions": "classement_conditions",
            "Odds ratios vs Témoin véhicule": "or_vs_temoin_vehicule",
            "Heatmap groupe × dilution": "heatmap_groupes_dilutions",
        }
        for index, (title, figure) in enumerate(figures.items(), start=1):
            st.subheader(title)
            display_figure_with_downloads(
                figure,
                f"drepano_{graph_names[title]}_{slugify(study_name)}",
                f"figure_{index}",
            )

with tabs[6]:
    st.header("Rapport et téléchargement global")
    st.caption(
        "Le rapport présente les méthodes, tableaux et figures sans formuler de conclusion biologique forte."
    )
    if not analysis_ready:
        st.info("Un fichier valide est nécessaire pour créer le rapport et l’archive.")
    else:
        study_info = {
            "Nom de l’étude": study_name,
            "Plante ou produit testé": product_name,
            "Groupes d’extraits": groups,
            "Dilutions": dilutions,
            "Témoins": controls,
            "Nombre de répétitions attendu": int(repetitions),
        }
        report_messages = [
            display_label(message)
            for message in [*validation_warnings, *glm_messages, *pairwise_warnings]
        ]
        report_bytes = generate_word_report(
            study_info,
            report_messages,
            descriptive_table,
            efficiency_ranking,
            group_ranking,
            glm_table,
            pairwise_table,
            figures,
        )
        tables = {
            "donnees_pretraitees": preprocessed_data,
            "tableau_descriptif": descriptive_table,
            "classement_conditions": efficiency_ranking,
            "classement_groupes": group_ranking,
            "glm_vs_temoin_vehicule": glm_table,
            "comparaisons_groupes": pairwise_table,
        }
        zip_bytes = generate_results_zip(tables, figures, report_bytes)
        download_columns = st.columns(2)
        with download_columns[0]:
            st.download_button(
                "Télécharger le rapport analytique Word",
                report_bytes,
                f"drepano_rapport_{slugify(study_name)}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with download_columns[1]:
            st.download_button(
                "Télécharger tous les résultats au format ZIP",
                zip_bytes,
                f"drepano_resultats_{slugify(study_name)}.zip",
                "application/zip",
                use_container_width=True,
            )

progress = 1 if uploaded_file is None else 3 if blocking_errors else 7
progress_placeholder.progress(progress / 7, text=f"Progression : étape {progress} sur 7")
if uploaded_file is None:
    status_placeholder.info("En attente du fichier rempli")
elif blocking_errors:
    status_placeholder.error("Fichier à corriger")
else:
    status_placeholder.success("Analyse prête")
