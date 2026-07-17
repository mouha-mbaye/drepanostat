"""Validation du fichier Excel rempli par l'utilisateur."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

REQUIRED_COLUMNS = [
    "type_condition",
    "groupe",
    "dilution",
    "temoin",
    "repetition",
    "N",
    "D",
    "commentaire",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + ["condition_standard"]
TEXT_COLUMNS = ["type_condition", "groupe", "dilution", "temoin", "commentaire"]
VALID_CONDITION_TYPES = {"Extrait", "Témoin"}


def _excel_rows(mask: pd.Series) -> str:
    """Convertit un masque pandas en liste de numéros de lignes Excel."""
    return ", ".join(str(int(index) + 2) for index in mask.index[mask])


def _add_row_error(errors: list[str], message: str, mask: pd.Series) -> None:
    if mask.any():
        errors.append(f"{message} Ligne(s) Excel : {_excel_rows(mask)}.")


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def validate_input_file(
    uploaded_file: str | Path | bytes | BinaryIO,
    expected_repetitions: int | None = None,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Lit et valide la feuille ``Données`` d'un classeur DrepanoStat.

    Returns:
        Un tuple ``(dataframe_nettoye, erreurs_bloquantes, avertissements)``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if expected_repetitions is not None:
        if (
            isinstance(expected_repetitions, bool)
            or not isinstance(expected_repetitions, int)
            or expected_repetitions < 1
        ):
            errors.append("expected_repetitions doit être un entier positif.")
            return _empty_result(), errors, warnings

    try:
        if isinstance(uploaded_file, bytes):
            uploaded_file = BytesIO(uploaded_file)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        excel_file = pd.ExcelFile(uploaded_file)
    except Exception as exc:
        errors.append(f"Le fichier Excel ne peut pas être lu : {exc}")
        return _empty_result(), errors, warnings

    if "Données" not in excel_file.sheet_names:
        errors.append('La feuille obligatoire "Données" est absente du fichier Excel.')
        return _empty_result(), errors, warnings

    try:
        dataframe = pd.read_excel(excel_file, sheet_name="Données", dtype=object)
    except Exception as exc:
        errors.append(f'La feuille "Données" ne peut pas être lue : {exc}')
        return _empty_result(), errors, warnings

    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        errors.append(
            "Colonne(s) obligatoire(s) absente(s) : " + ", ".join(missing_columns) + "."
        )
        return dataframe, errors, warnings

    dataframe = dataframe.loc[:, REQUIRED_COLUMNS].copy()
    dataframe = dataframe.dropna(how="all")

    if dataframe.empty:
        errors.append('La feuille "Données" ne contient aucune ligne de données.')
        return _empty_result(), errors, warnings

    # On conserve les index d'origine afin que index + 2 corresponde toujours à Excel.
    for column in TEXT_COLUMNS:
        dataframe[column] = dataframe[column].map(
            lambda value: pd.NA if pd.isna(value) or str(value).strip() == "" else str(value).strip()
        )

    invalid_type = ~dataframe["type_condition"].isin(VALID_CONDITION_TYPES)
    _add_row_error(
        errors,
        'type_condition doit contenir uniquement "Extrait" ou "Témoin".',
        invalid_type,
    )

    extract_mask = dataframe["type_condition"].eq("Extrait")
    control_mask = dataframe["type_condition"].eq("Témoin")
    _add_row_error(
        errors,
        'Le groupe doit être renseigné pour les lignes de type "Extrait".',
        extract_mask & dataframe["groupe"].isna(),
    )
    _add_row_error(
        errors,
        'La dilution doit être renseignée pour les lignes de type "Extrait".',
        extract_mask & dataframe["dilution"].isna(),
    )
    _add_row_error(
        errors,
        'Le témoin doit être renseigné pour les lignes de type "Témoin".',
        control_mask & dataframe["temoin"].isna(),
    )

    numeric_columns: dict[str, pd.Series] = {}
    for column in ("repetition", "N", "D"):
        original = dataframe[column]
        numeric = pd.to_numeric(original, errors="coerce")
        numeric_columns[column] = numeric

        missing = original.isna() | original.astype("string").str.strip().eq("").fillna(False)
        non_numeric = ~missing & numeric.isna()
        non_integer = numeric.notna() & numeric.mod(1).ne(0)

        _add_row_error(errors, f'La colonne "{column}" ne doit pas être vide.', missing)
        _add_row_error(
            errors,
            f'La colonne "{column}" doit contenir uniquement des valeurs numériques.',
            non_numeric,
        )
        _add_row_error(
            errors,
            f'La colonne "{column}" doit contenir uniquement des nombres entiers.',
            non_integer,
        )

    invalid_repetition_sign = numeric_columns["repetition"].notna() & numeric_columns[
        "repetition"
    ].le(0)
    _add_row_error(
        errors,
        'La colonne "repetition" doit contenir des entiers strictement positifs.',
        invalid_repetition_sign,
    )

    for column in ("N", "D"):
        negative = numeric_columns[column].notna() & numeric_columns[column].lt(0)
        _add_row_error(
            errors,
            f'La colonne "{column}" doit contenir des valeurs positives ou nulles.',
            negative,
        )

    valid_counts = numeric_columns["N"].notna() & numeric_columns["D"].notna()
    invalid_total = valid_counts & numeric_columns["N"].add(numeric_columns["D"]).le(0)
    _add_row_error(errors, "La somme N + D doit être strictement supérieure à 0.", invalid_total)

    vehicle_present = control_mask & dataframe["temoin"].astype("string").str.casefold().eq(
        "vehicle"
    ).fillna(False)
    if not vehicle_present.any():
        errors.append(
            "Le témoin Vehicle est absent. Il est nécessaire pour les comparaisons statistiques."
        )

    dataframe["condition_standard"] = pd.NA
    valid_extract_condition = extract_mask & dataframe["groupe"].notna() & dataframe[
        "dilution"
    ].notna()
    dataframe.loc[valid_extract_condition, "condition_standard"] = (
        dataframe.loc[valid_extract_condition, "groupe"].astype(str)
        + "_"
        + dataframe.loc[valid_extract_condition, "dilution"].astype(str)
    )
    valid_control_condition = control_mask & dataframe["temoin"].notna()
    dataframe.loc[valid_control_condition, "condition_standard"] = dataframe.loc[
        valid_control_condition, "temoin"
    ]

    for column in ("repetition", "N", "D"):
        integer_values = numeric_columns[column].where(
            numeric_columns[column].notna() & numeric_columns[column].mod(1).eq(0)
        )
        dataframe[column] = integer_values.astype("Int64")

    comparable_repetitions = dataframe["condition_standard"].notna() & dataframe[
        "repetition"
    ].notna()
    duplicate_mask = comparable_repetitions & dataframe.duplicated(
        subset=["condition_standard", "repetition"], keep=False
    )
    if duplicate_mask.any():
        duplicate_details: list[str] = []
        duplicates = dataframe.loc[duplicate_mask, ["condition_standard", "repetition"]]
        for condition, repetition in duplicates.drop_duplicates().itertuples(index=False):
            rows = duplicate_mask & dataframe["condition_standard"].eq(condition) & dataframe[
                "repetition"
            ].eq(repetition)
            duplicate_details.append(
                f"{condition}, répétition {int(repetition)} (lignes {_excel_rows(rows)})"
            )
        errors.append("Répétition(s) en doublon : " + "; ".join(duplicate_details) + ".")

    if expected_repetitions is not None:
        valid_conditions = dataframe.loc[
            dataframe["condition_standard"].notna(), "condition_standard"
        ].drop_duplicates()
        for condition in valid_conditions:
            repetitions = dataframe.loc[
                dataframe["condition_standard"].eq(condition) & dataframe["repetition"].notna(),
                "repetition",
            ].nunique()
            if repetitions < expected_repetitions:
                warnings.append(
                    f"La condition {condition} possède {repetitions} répétition(s) au lieu de "
                    f"{expected_repetitions} attendue(s)."
                )
            elif repetitions > expected_repetitions:
                warnings.append(
                    f"La condition {condition} possède {repetitions} répétition(s), soit plus que "
                    f"les {expected_repetitions} attendue(s)."
                )

    return dataframe.loc[:, OUTPUT_COLUMNS], errors, warnings


# Compatibilité avec le nom utilisé dans la première version de l'application.
validate_excel_file = validate_input_file
