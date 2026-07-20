"""Utilitaires d'affichage et de nommage pour l'interface DrepanoStat."""

from __future__ import annotations

import math
import re
import unicodedata

import pandas as pd

from src.display_labels import apply_display_labels

# Palette centrale : modifier ces valeurs suffit pour harmoniser toute l'application.
PALETTE = {
    "extract": "#2563EB",
    "control": "#6B7280",
    "significant": "#D97706",
    "non_significant": "#CBD5E1",
    "grid": "#E5E7EB",
    "text": "#111827",
}

SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def slugify(value: str, fallback: str = "etude") -> str:
    """Crée un fragment de nom de fichier lisible et portable."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    return slug or fallback


def _decimal_comma(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def _format_p_value(value: object) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    if number == 0:
        return "0"
    if abs(number) < 0.001:
        exponent = math.floor(math.log10(abs(number)))
        mantissa = number / (10**exponent)
        return f"{_decimal_comma(mantissa, 2)} × 10{str(exponent).translate(SUPERSCRIPT)}"
    return _decimal_comma(number, 4)


def format_table_for_display(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Retourne une copie lisible pour Streamlit, sans altérer les données numériques."""
    displayed = apply_display_labels(dataframe)
    for column in displayed.columns:
        lower = column.lower()
        if lower.startswith("prop_"):
            displayed[column] = displayed[column].map(
                lambda value: "" if pd.isna(value) else f"{_decimal_comma(float(value) * 100, 1)} %"
            )
        elif lower in {"or", "or_low95", "or_high95", "logor"}:
            displayed[column] = displayed[column].map(
                lambda value: "" if pd.isna(value) else _decimal_comma(float(value), 2)
            )
        elif lower in {"p_value", "p_value_holm"}:
            displayed[column] = displayed[column].map(_format_p_value)
        elif lower.startswith("significatif"):
            displayed[column] = displayed[column].map(
                lambda value: "" if pd.isna(value) else "Oui" if bool(value) else "Non"
            )
    return displayed

