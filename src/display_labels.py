"""Libellés français destinés à l'affichage, sans modifier les données internes."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

DISPLAY_LABELS = {
    "Vehicle": "Témoin véhicule",
    "Emmel": "Témoin Emmel",
}
INTERNAL_LABELS = {label: value for value, label in DISPLAY_LABELS.items()}


def display_label(value: Any) -> Any:
    """Traduit un libellé interne, y compris lorsqu'il apparaît dans une phrase."""
    if not isinstance(value, str):
        return value
    if value in DISPLAY_LABELS:
        return DISPLAY_LABELS[value]
    if value in INTERNAL_LABELS:
        return value
    displayed = re.sub(r"\bVehicle\b", DISPLAY_LABELS["Vehicle"], value)
    displayed = re.sub(r"(?<!Témoin )\bEmmel\b", DISPLAY_LABELS["Emmel"], displayed)
    return displayed


def internal_label(value: Any) -> Any:
    """Rétablit un libellé interne lorsqu'une valeur provient de l'interface."""
    if not isinstance(value, str):
        return value
    return INTERNAL_LABELS.get(value, value)


def apply_display_labels(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Retourne une copie d'affichage ; le dataframe source reste inchangé."""
    displayed = dataframe.copy()
    for column in displayed.columns:
        if pd.api.types.is_object_dtype(displayed[column].dtype) or isinstance(
            displayed[column].dtype, pd.StringDtype
        ):
            displayed[column] = displayed[column].map(display_label)
    return displayed

