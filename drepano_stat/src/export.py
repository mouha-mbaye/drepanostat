"""Exports groupés des résultats DrepanoStat."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from matplotlib.figure import Figure

from src.display_labels import apply_display_labels
from src.plots import save_figure_to_bytes


def _safe_name(name: str) -> str:
    safe = "".join(character if character.isalnum() or character in "-_" else "_" for character in name)
    return safe.strip("_") or "resultat"


def generate_results_zip(
    tables: Mapping[str, pd.DataFrame],
    figures: Mapping[str, Figure],
    report_bytes: bytes | None = None,
) -> bytes:
    """Regroupe les tableaux CSV, figures PNG/SVG et éventuellement le rapport Word."""
    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as archive:
        for name, table in tables.items():
            filename = _safe_name(str(name))
            displayed = apply_display_labels(table)
            archive.writestr(
                str(PurePosixPath("tableaux") / f"{filename}.csv"),
                displayed.to_csv(index=False).encode("utf-8-sig"),
            )
        for name, figure in figures.items():
            filename = _safe_name(str(name))
            archive.writestr(
                str(PurePosixPath("figures") / f"{filename}.png"),
                save_figure_to_bytes(figure, format="png", dpi=300),
            )
            archive.writestr(
                str(PurePosixPath("figures") / f"{filename}.svg"),
                save_figure_to_bytes(figure, format="svg", dpi=300),
            )
        if report_bytes is not None:
            archive.writestr("rapport_analytique_drepano_stat.docx", report_bytes)
    return output.getvalue()
