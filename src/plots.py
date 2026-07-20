"""Graphiques statiques de qualité publication pour DrepanoStat."""

from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from src.display_labels import display_label
from src.utils import PALETTE

EXTRACT_COLOR = PALETTE["extract"]
CONTROL_COLOR = PALETTE["control"]
SIGNIFICANT_COLOR = PALETTE["significant"]
NON_SIGNIFICANT_COLOR = PALETTE["non_significant"]


def _apply_publication_style() -> None:
    """Applique un style homogène, sobre et lisible à matplotlib."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
        }
    )


def _empty_figure(title: str, message: str = "Données insuffisantes") -> Figure:
    _apply_publication_style()
    figure, axis = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
    axis.set_title(title)
    axis.text(0.5, 0.5, message, ha="center", va="center", transform=axis.transAxes)
    axis.set_axis_off()
    return figure


def _has_columns(dataframe: pd.DataFrame, columns: set[str]) -> bool:
    return isinstance(dataframe, pd.DataFrame) and columns.issubset(dataframe.columns)


def _condition_colors(dataframe: pd.DataFrame) -> list[str]:
    return [
        EXTRACT_COLOR if value == "Extrait" else CONTROL_COLOR
        for value in dataframe["type_condition"]
    ]


def _vertical_condition_plot(
    descriptive_table: pd.DataFrame,
    mean_column: str,
    sd_column: str,
    ylabel: str,
    title: str,
) -> Figure:
    required = {"condition_label", mean_column, sd_column, "type_condition"}
    if not _has_columns(descriptive_table, required) or descriptive_table.empty:
        return _empty_figure(title)

    data = descriptive_table.loc[:, list(required)].copy()
    data["condition_label"] = data["condition_label"].map(display_label)
    data[mean_column] = pd.to_numeric(data[mean_column], errors="coerce")
    data[sd_column] = pd.to_numeric(data[sd_column], errors="coerce").fillna(0).clip(lower=0)
    data = data.dropna(subset=["condition_label", mean_column])
    if data.empty:
        return _empty_figure(title)

    _apply_publication_style()
    width = max(8.0, 0.62 * len(data))
    figure, axis = plt.subplots(figsize=(width, 5.5), constrained_layout=True)
    positions = np.arange(len(data))
    axis.bar(
        positions,
        data[mean_column],
        yerr=data[sd_column],
        color=_condition_colors(data),
        edgecolor="white",
        linewidth=0.6,
        capsize=3,
        error_kw={"elinewidth": 1, "ecolor": "#374151"},
    )
    axis.set_xticks(positions, data["condition_label"].astype(str))
    rotation = 45 if len(data) > 5 or data["condition_label"].astype(str).str.len().max() > 12 else 0
    axis.tick_params(axis="x", labelrotation=rotation)
    if rotation:
        plt.setp(axis.get_xticklabels(), ha="right")
    upper = max(1.0, float((data[mean_column] + data[sd_column]).max()) * 1.08)
    axis.set_ylim(0, upper)
    axis.set_ylabel(ylabel)
    axis.set_xlabel("Condition")
    axis.set_title(title, pad=12)
    axis.yaxis.grid(True, color="#E5E7EB", linewidth=0.7)
    axis.set_axisbelow(True)
    return figure


def plot_prop_drepano_by_condition(descriptive_table: pd.DataFrame) -> Figure:
    """Barplot des proportions moyennes de drépanocytes par condition."""
    return _vertical_condition_plot(
        descriptive_table,
        "prop_drepano_moyenne",
        "prop_drepano_sd",
        "Proportion moyenne de drépanocytes",
        "Proportion moyenne de drépanocytes par condition",
    )


def plot_prop_normal_by_condition(descriptive_table: pd.DataFrame) -> Figure:
    """Barplot des proportions moyennes de globules rouges normaux."""
    return _vertical_condition_plot(
        descriptive_table,
        "prop_normal_moyenne",
        "prop_normal_sd",
        "Proportion moyenne de globules rouges normaux",
        "Proportion moyenne de globules rouges normaux par condition",
    )


def plot_efficiency_ranking(ranking_table: pd.DataFrame) -> Figure:
    """Classement horizontal des conditions, de la plus efficace à la moins efficace."""
    title = "Classement d’efficacité des conditions"
    required = {"rang", "condition_label", "prop_drepano_moyenne"}
    if not _has_columns(ranking_table, required) or ranking_table.empty:
        return _empty_figure(title)

    data = ranking_table.copy()
    data["condition_label"] = data["condition_label"].map(display_label)
    data["prop_drepano_moyenne"] = pd.to_numeric(
        data["prop_drepano_moyenne"], errors="coerce"
    )
    data = data.dropna(subset=["condition_label", "prop_drepano_moyenne"]).sort_values(
        "prop_drepano_moyenne", ascending=True, kind="stable"
    )
    if data.empty:
        return _empty_figure(title)

    _apply_publication_style()
    height = max(4.0, 0.42 * len(data) + 1.5)
    figure, axis = plt.subplots(figsize=(8.5, height), constrained_layout=True)
    positions = np.arange(len(data))
    axis.barh(positions, data["prop_drepano_moyenne"], color=EXTRACT_COLOR, height=0.7)
    axis.set_yticks(positions, data["condition_label"].astype(str))
    axis.invert_yaxis()
    axis.set_xlim(0, max(1.0, float(data["prop_drepano_moyenne"].max()) * 1.08))
    axis.set_xlabel("Proportion moyenne de drépanocytes")
    axis.set_ylabel("Condition")
    axis.set_title(title, pad=12)
    axis.xaxis.grid(True, color="#E5E7EB", linewidth=0.7)
    axis.set_axisbelow(True)
    return figure


def plot_or_vs_vehicle(glm_results_table: pd.DataFrame) -> Figure:
    """Forest plot des odds ratios des extraits par rapport au Vehicle."""
    title = "Odds ratios des extraits par rapport au Témoin véhicule"
    required = {"condition_label", "OR", "OR_low95", "OR_high95", "significatif_0_05"}
    if not _has_columns(glm_results_table, required) or glm_results_table.empty:
        return _empty_figure(title, "Aucun résultat GLM disponible")

    data = glm_results_table.copy()
    data["condition_label"] = data["condition_label"].map(display_label)
    for column in ("OR", "OR_low95", "OR_high95"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    finite_positive = (
        np.isfinite(data[["OR", "OR_low95", "OR_high95"]]).all(axis=1)
        & data[["OR", "OR_low95", "OR_high95"]].gt(0).all(axis=1)
    )
    data = data.loc[finite_positive].sort_values("OR", ascending=True, kind="stable")
    if data.empty:
        return _empty_figure(title, "Odds ratios non représentables")

    _apply_publication_style()
    height = max(4.0, 0.45 * len(data) + 1.7)
    figure, axis = plt.subplots(figsize=(9, height), constrained_layout=True)
    positions = np.arange(len(data))
    significant = data["significatif_0_05"].fillna(False).astype(bool)
    colors = np.where(significant, SIGNIFICANT_COLOR, NON_SIGNIFICANT_COLOR)
    lower_errors = data["OR"] - data["OR_low95"]
    upper_errors = data["OR_high95"] - data["OR"]
    for position, (_, row), color in zip(positions, data.iterrows(), colors, strict=True):
        axis.errorbar(
            row["OR"],
            position,
            xerr=np.array([[row["OR"] - row["OR_low95"]], [row["OR_high95"] - row["OR"]]]),
            fmt="o",
            color=color,
            ecolor=color,
            markersize=6,
            capsize=3,
            elinewidth=1.4,
        )
    axis.axvline(1, color="#111827", linestyle="--", linewidth=1)
    axis.set_xscale("log")
    axis.set_yticks(positions, data["condition_label"].astype(str))
    axis.set_xlabel("Odds ratio (échelle logarithmique)")
    axis.set_ylabel("Condition")
    axis.set_title(title, pad=12)
    axis.xaxis.grid(True, color="#E5E7EB", linewidth=0.7, which="both")
    axis.set_axisbelow(True)
    return figure


def plot_group_dilution_heatmap(descriptive_table: pd.DataFrame) -> Figure:
    """Heatmap groupe × dilution des proportions moyennes de drépanocytes."""
    title = "Heatmap des proportions moyennes de drépanocytes"
    required = {"groupe", "dilution", "prop_drepano_moyenne", "type_condition"}
    if not _has_columns(descriptive_table, required) or descriptive_table.empty:
        return _empty_figure(title)

    extracts = descriptive_table.loc[descriptive_table["type_condition"].eq("Extrait")].copy()
    extracts["prop_drepano_moyenne"] = pd.to_numeric(
        extracts["prop_drepano_moyenne"], errors="coerce"
    )
    extracts = extracts.dropna(subset=["groupe", "dilution", "prop_drepano_moyenne"])
    if extracts["groupe"].nunique() < 2 or extracts["dilution"].nunique() < 2:
        return _empty_figure(title, "Au moins deux groupes et deux dilutions sont nécessaires")

    matrix = extracts.pivot_table(
        index="groupe",
        columns="dilution",
        values="prop_drepano_moyenne",
        aggfunc="mean",
        sort=False,
    )
    _apply_publication_style()
    width = max(6.5, 1.15 * len(matrix.columns) + 2.5)
    height = max(4.0, 0.7 * len(matrix.index) + 2.0)
    figure, axis = plt.subplots(figsize=(width, height), constrained_layout=True)
    image = axis.imshow(matrix.to_numpy(dtype=float), cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
    axis.set_xticks(np.arange(len(matrix.columns)), matrix.columns.astype(str))
    axis.set_yticks(np.arange(len(matrix.index)), matrix.index.astype(str))
    axis.set_xlabel("Dilution")
    axis.set_ylabel("Groupe")
    axis.set_title(title, pad=12)
    if len(matrix.columns) > 5:
        axis.tick_params(axis="x", labelrotation=45)
        plt.setp(axis.get_xticklabels(), ha="right")
    values = matrix.to_numpy(dtype=float)
    for row in range(values.shape[0]):
        for column in range(values.shape[1]):
            value = values[row, column]
            if np.isfinite(value):
                text_color = "white" if value >= 0.55 else "#111827"
                axis.text(column, row, f"{value:.3f}", ha="center", va="center", color=text_color)
    colorbar = figure.colorbar(image, ax=axis, shrink=0.85)
    colorbar.set_label("Proportion moyenne de drépanocytes")
    return figure


def save_figure_to_bytes(fig: Figure, format: str = "png", dpi: int = 300) -> bytes:
    """Sérialise une figure en PNG, SVG ou PDF."""
    output_format = format.lower().strip()
    if output_format not in {"png", "svg", "pdf"}:
        raise ValueError("Le format doit être png, svg ou pdf.")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi < 1:
        raise ValueError("dpi doit être un entier positif.")
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format=output_format,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
    )
    return buffer.getvalue()
