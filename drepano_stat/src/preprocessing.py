"""Prétraitement des données validées de DrepanoStat."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "type_condition",
    "groupe",
    "dilution",
    "temoin",
    "repetition",
    "N",
    "D",
]


def preprocess_data(df_validated: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les totaux, proportions et libellés standardisés.

    Le dataframe d'entrée n'est pas modifié. Cette fonction suppose que les
    données ont déjà passé la validation bloquante de ``validation.py``.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in df_validated.columns]
    if missing:
        raise ValueError("Colonnes nécessaires absentes : " + ", ".join(missing) + ".")

    dataframe = df_validated.copy()
    dataframe["N"] = pd.to_numeric(dataframe["N"], errors="raise")
    dataframe["D"] = pd.to_numeric(dataframe["D"], errors="raise")
    dataframe["total"] = dataframe["N"] + dataframe["D"]

    if dataframe["total"].isna().any() or dataframe["total"].le(0).any():
        raise ValueError("Chaque ligne doit avoir un total N + D strictement positif.")

    dataframe["prop_normal"] = dataframe["N"] / dataframe["total"]
    dataframe["prop_drepano"] = dataframe["D"] / dataframe["total"]

    extract_mask = dataframe["type_condition"].eq("Extrait")
    control_mask = dataframe["type_condition"].eq("Témoin")
    invalid_type = ~(extract_mask | control_mask)
    if invalid_type.any():
        raise ValueError('type_condition doit contenir uniquement "Extrait" ou "Témoin".')

    dataframe["condition_standard"] = pd.NA
    dataframe["condition_label"] = pd.NA
    dataframe.loc[extract_mask, "condition_standard"] = (
        dataframe.loc[extract_mask, "groupe"].astype(str)
        + "_"
        + dataframe.loc[extract_mask, "dilution"].astype(str)
    )
    dataframe.loc[extract_mask, "condition_label"] = (
        dataframe.loc[extract_mask, "groupe"].astype(str)
        + " - "
        + dataframe.loc[extract_mask, "dilution"].astype(str)
    )
    dataframe.loc[control_mask, "condition_standard"] = dataframe.loc[
        control_mask, "temoin"
    ]
    dataframe.loc[control_mask, "condition_label"] = dataframe.loc[control_mask, "temoin"]

    return dataframe

