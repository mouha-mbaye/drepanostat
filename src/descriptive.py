"""Tableaux descriptifs et classements d'efficacité."""

from __future__ import annotations

import pandas as pd

DESCRIPTIVE_COLUMNS = [
    "condition_standard",
    "condition_label",
    "type_condition",
    "groupe",
    "dilution",
    "temoin",
    "N_total",
    "D_total",
    "total",
    "prop_normal_moyenne",
    "prop_drepano_moyenne",
    "prop_drepano_sd",
    "prop_normal_sd",
    "n_repetitions",
]


def _require_preprocessed_columns(dataframe: pd.DataFrame) -> None:
    required = {
        "condition_standard",
        "condition_label",
        "type_condition",
        "groupe",
        "dilution",
        "temoin",
        "repetition",
        "N",
        "D",
        "total",
        "prop_normal",
        "prop_drepano",
    }
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError("Colonnes prétraitées absentes : " + ", ".join(missing) + ".")


def make_descriptive_table(df: pd.DataFrame) -> pd.DataFrame:
    """Produit un résumé des comptages et proportions par condition."""
    _require_preprocessed_columns(df)
    if df.empty:
        return pd.DataFrame(columns=DESCRIPTIVE_COLUMNS)

    table = (
        df.groupby("condition_standard", sort=False, dropna=False)
        .agg(
            condition_label=("condition_label", "first"),
            type_condition=("type_condition", "first"),
            groupe=("groupe", "first"),
            dilution=("dilution", "first"),
            temoin=("temoin", "first"),
            N_total=("N", "sum"),
            D_total=("D", "sum"),
            total=("total", "sum"),
            prop_normal_moyenne=("prop_normal", "mean"),
            prop_drepano_moyenne=("prop_drepano", "mean"),
            prop_drepano_sd=("prop_drepano", "std"),
            prop_normal_sd=("prop_normal", "std"),
            n_repetitions=("repetition", "nunique"),
        )
        .reset_index()
    )
    return table.loc[:, DESCRIPTIVE_COLUMNS]


def make_efficiency_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Classe les conditions Extrait par proportion moyenne de drépanocytes."""
    descriptive = make_descriptive_table(df)
    columns = [
        "rang",
        "condition_standard",
        "condition_label",
        "groupe",
        "dilution",
        "prop_drepano_moyenne",
        "prop_normal_moyenne",
        "N_total",
        "D_total",
        "total",
        "n_repetitions",
    ]
    ranking = descriptive.loc[descriptive["type_condition"].eq("Extrait")].copy()
    ranking = ranking.sort_values(
        ["prop_drepano_moyenne", "condition_standard"],
        ascending=[True, True],
        kind="stable",
    ).reset_index(drop=True)
    ranking.insert(0, "rang", range(1, len(ranking) + 1))
    return ranking.loc[:, columns]


def make_group_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """Classe globalement les groupes d'extraits sur toutes leurs répétitions."""
    _require_preprocessed_columns(df)
    columns = [
        "rang",
        "groupe",
        "prop_drepano_moyenne",
        "prop_normal_moyenne",
        "N_total",
        "D_total",
        "total",
        "n_conditions",
        "n_repetitions_total",
    ]
    extracts = df.loc[df["type_condition"].eq("Extrait")]
    if extracts.empty:
        return pd.DataFrame(columns=columns)

    ranking = (
        extracts.groupby("groupe", sort=False, dropna=False)
        .agg(
            prop_drepano_moyenne=("prop_drepano", "mean"),
            prop_normal_moyenne=("prop_normal", "mean"),
            N_total=("N", "sum"),
            D_total=("D", "sum"),
            total=("total", "sum"),
            n_conditions=("condition_standard", "nunique"),
            n_repetitions_total=("repetition", "count"),
        )
        .reset_index()
        .sort_values(
            ["prop_drepano_moyenne", "groupe"],
            ascending=[True, True],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    ranking.insert(0, "rang", range(1, len(ranking) + 1))
    return ranking.loc[:, columns]

