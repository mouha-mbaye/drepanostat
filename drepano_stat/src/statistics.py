"""Modèles statistiques de DrepanoStat."""

from __future__ import annotations

from itertools import combinations
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

RESULT_COLUMNS = [
    "condition_standard",
    "condition_label",
    "reference",
    "coefficient",
    "erreur_standard",
    "z",
    "p_value",
    "OR",
    "OR_low95",
    "OR_high95",
    "p_value_holm",
    "significatif_0_05",
    "interpretation",
]

REQUIRED_COLUMNS = {
    "type_condition",
    "groupe",
    "dilution",
    "temoin",
    "condition_standard",
    "condition_label",
    "N",
    "D",
    "total",
    "prop_normal",
    "prop_drepano",
}

PAIRWISE_RESULT_COLUMNS = [
    "dilution",
    "groupe_1",
    "groupe_2",
    "comparaison",
    "logOR",
    "erreur_standard",
    "z",
    "p_value",
    "OR",
    "OR_low95",
    "OR_high95",
    "p_value_holm",
    "significatif_0_05",
    "interpretation",
]


def _empty_results() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def _interpretation(odds_ratio: float, adjusted_p_value: float, alpha: float) -> str:
    significant = adjusted_p_value < alpha
    if odds_ratio > 1 and significant:
        return (
            "Augmentation significative des chances d'observer des globules rouges "
            "normaux par rapport au Vehicle."
        )
    if odds_ratio > 1 and not significant:
        return (
            "Augmentation non significative des chances d'observer des globules rouges "
            "normaux par rapport au Vehicle."
        )
    if odds_ratio < 1 and significant:
        return (
            "Diminution significative des chances d'observer des globules rouges "
            "normaux par rapport au Vehicle."
        )
    return "Différence non significative par rapport au Vehicle."


def run_glm_vs_vehicle(
    df: pd.DataFrame,
    reference: str = "Vehicle",
    alpha: float = 0.05,
) -> tuple[pd.DataFrame, object | None, list[str]]:
    """Compare chaque condition d'extrait au témoin par GLM binomial.

    La réponse du modèle est constituée des comptages groupés ``[N, D]`` : le
    succès est un globule rouge normal et l'échec un globule rouge
    drépanocytaire. Le troisième élément retourné contient les erreurs ou
    avertissements préfixés par leur niveau.
    """
    messages: list[str] = []

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        messages.append("Erreur : colonnes nécessaires absentes : " + ", ".join(missing) + ".")
        return _empty_results(), None, messages
    if not 0 < alpha < 1:
        messages.append("Erreur : alpha doit être strictement compris entre 0 et 1.")
        return _empty_results(), None, messages

    reference_mask = df["type_condition"].eq("Témoin") & df["temoin"].eq(reference)
    extract_mask = df["type_condition"].eq("Extrait")
    if not reference_mask.any():
        messages.append(f"Erreur : le témoin de référence {reference} est absent.")
        return _empty_results(), None, messages
    if not extract_mask.any():
        messages.append("Erreur : aucune condition d’extrait n’est disponible pour le modèle.")
        return _empty_results(), None, messages

    # Ce filtre exclut explicitement Emmel et tout autre témoin non sélectionné.
    analysis = df.loc[reference_mask | extract_mask].copy()
    numeric = analysis[["N", "D"]].apply(pd.to_numeric, errors="coerce")
    invalid_counts = numeric.isna().any(axis=1) | numeric.lt(0).any(axis=1)
    invalid_totals = numeric.sum(axis=1).le(0)
    if invalid_counts.any() or invalid_totals.any():
        messages.append(
            "Erreur : le modèle requiert des comptages N et D valides et un total strictement positif."
        )
        return _empty_results(), None, messages
    analysis[["N", "D"]] = numeric

    extract_conditions = list(
        analysis.loc[analysis["type_condition"].eq("Extrait"), "condition_standard"]
        .dropna()
        .drop_duplicates()
    )
    if not extract_conditions:
        messages.append("Erreur : aucune condition_standard d’extrait valide n’a été trouvée.")
        return _empty_results(), None, messages

    # La constante représente explicitement la modalité de référence.
    exog = pd.DataFrame({"const": np.ones(len(analysis), dtype=float)}, index=analysis.index)
    parameter_names: dict[str, str] = {}
    for index, condition in enumerate(extract_conditions, start=1):
        parameter_name = f"condition_{index}"
        parameter_names[condition] = parameter_name
        exog[parameter_name] = analysis["condition_standard"].eq(condition).astype(float)

    endog = analysis[["N", "D"]].to_numpy(dtype=float)
    fitted_model = None
    try:
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            fitted_model = sm.GLM(endog, exog, family=sm.families.Binomial()).fit()
        for warning in caught_warnings:
            text = str(warning.message)
            message = f"Avertissement statsmodels : {text}"
            if message not in messages:
                messages.append(message)
    except Exception as exc:
        messages.append(f"Erreur : le GLM binomial n’a pas pu être ajusté : {exc}")
        return _empty_results(), None, messages

    if not bool(getattr(fitted_model, "converged", False)):
        messages.append("Erreur : le GLM binomial n’a pas convergé.")
        return _empty_results(), fitted_model, messages

    rows: list[dict[str, object]] = []
    for condition in extract_conditions:
        parameter = parameter_names[condition]
        coefficient = float(fitted_model.params[parameter])
        standard_error = float(fitted_model.bse[parameter])
        z_value = float(fitted_model.tvalues[parameter])
        p_value = float(fitted_model.pvalues[parameter])
        label_values = analysis.loc[
            analysis["condition_standard"].eq(condition), "condition_label"
        ].dropna()
        condition_label = label_values.iloc[0] if not label_values.empty else condition
        rows.append(
            {
                "condition_standard": condition,
                "condition_label": condition_label,
                "reference": reference,
                "coefficient": coefficient,
                "erreur_standard": standard_error,
                "z": z_value,
                "p_value": p_value,
                "OR": float(np.exp(coefficient)),
                "OR_low95": float(np.exp(coefficient - 1.96 * standard_error)),
                "OR_high95": float(np.exp(coefficient + 1.96 * standard_error)),
            }
        )

    results = pd.DataFrame(rows)
    if not np.isfinite(results["p_value"].to_numpy(dtype=float)).all():
        messages.append("Erreur : le modèle a produit au moins une p-value non finie.")
        return _empty_results(), fitted_model, messages

    results["p_value_holm"] = multipletests(
        results["p_value"].to_numpy(dtype=float), alpha=alpha, method="holm"
    )[1]
    results["significatif_0_05"] = results["p_value_holm"].lt(alpha)
    results["interpretation"] = [
        _interpretation(odds_ratio, adjusted_p_value, alpha)
        for odds_ratio, adjusted_p_value in zip(
            results["OR"], results["p_value_holm"], strict=True
        )
    ]
    return results.loc[:, RESULT_COLUMNS], fitted_model, messages


def _empty_pairwise_results() -> pd.DataFrame:
    return pd.DataFrame(columns=PAIRWISE_RESULT_COLUMNS)


def _pairwise_interpretation(
    group_1: str,
    group_2: str,
    odds_ratio: float,
    adjusted_p_value: float,
    alpha: float,
) -> str:
    if adjusted_p_value >= alpha:
        return "Aucune différence significative entre les deux groupes pour cette dilution."
    if odds_ratio > 1:
        return (
            f"Le groupe {group_1} est significativement plus efficace que le groupe {group_2} "
            "pour cette dilution."
        )
    if odds_ratio < 1:
        return (
            f"Le groupe {group_2} est significativement plus efficace que le groupe {group_1} "
            "pour cette dilution."
        )
    return "Aucune différence significative entre les deux groupes pour cette dilution."


def run_pairwise_group_comparisons(
    df: pd.DataFrame,
    alpha: float = 0.05,
) -> tuple[pd.DataFrame, list[str]]:
    """Compare tous les groupes d'extraits deux à deux dans chaque dilution.

    Un GLM binomial sur les comptages groupés ``[N, D]`` est ajusté séparément
    pour chaque dilution. Les avertissements d'une dilution n'empêchent pas le
    traitement des autres dilutions.
    """
    warnings_list: list[str] = []
    required = {
        "type_condition",
        "groupe",
        "dilution",
        "condition_standard",
        "condition_label",
        "N",
        "D",
        "total",
        "prop_normal",
        "prop_drepano",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        warnings_list.append(
            "Analyse entre groupes impossible : colonnes absentes : " + ", ".join(missing) + "."
        )
        return _empty_pairwise_results(), warnings_list
    if not 0 < alpha < 1:
        warnings_list.append("Analyse entre groupes impossible : alpha doit être compris entre 0 et 1.")
        return _empty_pairwise_results(), warnings_list

    extracts = df.loc[df["type_condition"].eq("Extrait")].copy()
    if extracts.empty:
        warnings_list.append("Aucune ligne d’extrait n’est disponible pour les comparaisons entre groupes.")
        return _empty_pairwise_results(), warnings_list

    dilutions = extracts["dilution"].dropna().drop_duplicates().tolist()
    if not dilutions:
        warnings_list.append("Aucune dilution valide n’a été trouvée parmi les extraits.")
        return _empty_pairwise_results(), warnings_list

    rows: list[dict[str, object]] = []
    for dilution in dilutions:
        subset = extracts.loc[extracts["dilution"].eq(dilution)].copy()
        groups = subset["groupe"].dropna().drop_duplicates().tolist()
        if len(groups) < 2:
            warnings_list.append(
                f"Dilution {dilution} ignorée : au moins deux groupes sont nécessaires."
            )
            continue

        numeric = subset[["N", "D"]].apply(pd.to_numeric, errors="coerce")
        invalid = numeric.isna().any(axis=1) | numeric.lt(0).any(axis=1) | numeric.sum(axis=1).le(0)
        if invalid.any():
            warnings_list.append(
                f"Dilution {dilution} ignorée : comptages N/D invalides ou données insuffisantes."
            )
            continue
        subset[["N", "D"]] = numeric

        boundary_groups: list[str] = []
        for group in groups:
            group_counts = subset.loc[subset["groupe"].eq(group), ["N", "D"]]
            if group_counts["N"].sum() == 0 or group_counts["D"].sum() == 0:
                boundary_groups.append(str(group))
        if boundary_groups:
            warnings_list.append(
                f"Dilution {dilution} ignorée : le(s) groupe(s) "
                + ", ".join(boundary_groups)
                + " présente(nt) uniquement N = 0 ou uniquement D = 0."
            )
            continue

        # Sans constante, chaque paramètre représente le log-odds propre au groupe.
        exog = pd.DataFrame(index=subset.index)
        parameter_names: dict[str, str] = {}
        for index, group in enumerate(groups, start=1):
            parameter = f"group_{index}"
            parameter_names[group] = parameter
            exog[parameter] = subset["groupe"].eq(group).astype(float)

        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                fitted = sm.GLM(
                    subset[["N", "D"]].to_numpy(dtype=float),
                    exog,
                    family=sm.families.Binomial(),
                ).fit()
            for warning in caught_warnings:
                text = str(warning.message)
                message = f"Dilution {dilution} — avertissement statsmodels : {text}"
                if message not in warnings_list:
                    warnings_list.append(message)
        except Exception as exc:
            warnings_list.append(
                f"Dilution {dilution} ignorée : le GLM binomial n’a pas pu être ajusté ({exc})."
            )
            continue

        if not bool(getattr(fitted, "converged", False)):
            warnings_list.append(f"Dilution {dilution} ignorée : le GLM binomial n’a pas convergé.")
            continue

        covariance = fitted.cov_params()
        for group_1, group_2 in combinations(groups, 2):
            parameter_1 = parameter_names[group_1]
            parameter_2 = parameter_names[group_2]
            log_odds_ratio = float(fitted.params[parameter_1] - fitted.params[parameter_2])
            variance = float(
                covariance.loc[parameter_1, parameter_1]
                + covariance.loc[parameter_2, parameter_2]
                - 2 * covariance.loc[parameter_1, parameter_2]
            )
            if not np.isfinite(variance) or variance <= 0:
                warnings_list.append(
                    f"Comparaison {group_1} vs {group_2} à {dilution} ignorée : "
                    "erreur standard non calculable."
                )
                continue
            standard_error = float(np.sqrt(variance))
            contrast = np.zeros(len(groups), dtype=float)
            contrast[groups.index(group_1)] = 1.0
            contrast[groups.index(group_2)] = -1.0
            contrast_test = fitted.t_test(contrast)
            z_value = log_odds_ratio / standard_error
            p_value = float(np.asarray(contrast_test.pvalue).item())
            rows.append(
                {
                    "dilution": dilution,
                    "groupe_1": group_1,
                    "groupe_2": group_2,
                    "comparaison": f"{group_1} vs {group_2}",
                    "logOR": log_odds_ratio,
                    "erreur_standard": standard_error,
                    "z": z_value,
                    "p_value": p_value,
                    "OR": float(np.exp(log_odds_ratio)),
                    "OR_low95": float(np.exp(log_odds_ratio - 1.96 * standard_error)),
                    "OR_high95": float(np.exp(log_odds_ratio + 1.96 * standard_error)),
                }
            )

    if not rows:
        return _empty_pairwise_results(), warnings_list

    results = pd.DataFrame(rows)
    finite_p_values = np.isfinite(results["p_value"].to_numpy(dtype=float))
    if not finite_p_values.all():
        removed = int((~finite_p_values).sum())
        warnings_list.append(
            f"{removed} comparaison(s) ignorée(s), car leur p-value n’était pas calculable."
        )
        results = results.loc[finite_p_values].copy()
    if results.empty:
        return _empty_pairwise_results(), warnings_list

    results["p_value_holm"] = multipletests(
        results["p_value"].to_numpy(dtype=float), alpha=alpha, method="holm"
    )[1]
    results["significatif_0_05"] = results["p_value_holm"].lt(alpha)
    results["interpretation"] = [
        _pairwise_interpretation(group_1, group_2, odds_ratio, adjusted_p, alpha)
        for group_1, group_2, odds_ratio, adjusted_p in zip(
            results["groupe_1"],
            results["groupe_2"],
            results["OR"],
            results["p_value_holm"],
            strict=True,
        )
    ]
    return results.loc[:, PAIRWISE_RESULT_COLUMNS], warnings_list
