"""OLS, Spatial Lag, and Spatial Error regression, with subgroup analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd


def _design_matrix(gdf: gpd.GeoDataFrame, dependent: str, covariates: list[str]) -> tuple:
    df = gdf[[dependent] + covariates].dropna()
    y = df[dependent].values
    X = np.column_stack([np.ones(len(df))] + [df[c].values for c in covariates])
    return y, X, df.index


def run_ols(
    gdf: gpd.GeoDataFrame,
    dependent: str,
    covariates: list[str],
) -> dict:
    """OLS regression with HC3 robust standard errors."""
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant

    df = gdf[[dependent] + covariates].dropna()
    y = df[dependent]
    X = add_constant(df[covariates])
    model = OLS(y, X).fit(cov_type="HC3")

    return {
        "method": "OLS",
        "n": int(model.nobs),
        "r_squared": round(float(model.rsquared), 4),
        "adj_r_squared": round(float(model.rsquared_adj), 4),
        "aic": round(float(model.aic), 2),
        "coefficients": {
            str(k): {
                "coef": round(float(v), 6),
                "p_value": round(float(model.pvalues[k]), 6),
            }
            for k, v in model.params.items()
        },
    }


def run_spatial_lag(
    gdf: gpd.GeoDataFrame,
    dependent: str,
    covariates: list[str],
    weights,
) -> dict:
    """Spatial Lag model (ML_Lag): W×y enters as additional predictor."""
    try:
        from spreg import ML_Lag
    except ImportError:
        return {"method": "SpatialLag", "error": "spreg not installed"}

    df = gdf[[dependent] + covariates].dropna()
    y = df[dependent].values.reshape(-1, 1)
    X = df[covariates].values

    model = ML_Lag(y, X, weights, name_y=dependent, name_x=covariates)
    return {
        "method": "SpatialLag",
        "n": int(model.n),
        "r_squared": round(float(model.pr2), 4),
        "aic": round(float(model.aic), 2),
        "rho": round(float(model.rho), 6),
    }


def run_spatial_error(
    gdf: gpd.GeoDataFrame,
    dependent: str,
    covariates: list[str],
    weights,
) -> dict:
    """Spatial Error model (ML_Error): spatially autocorrelated residuals."""
    try:
        from spreg import ML_Error
    except ImportError:
        return {"method": "SpatialError", "error": "spreg not installed"}

    df = gdf[[dependent] + covariates].dropna()
    y = df[dependent].values.reshape(-1, 1)
    X = df[covariates].values

    model = ML_Error(y, X, weights, name_y=dependent, name_x=covariates)
    return {
        "method": "SpatialError",
        "n": int(model.n),
        "r_squared": round(float(model.pr2), 4),
        "aic": round(float(model.aic), 2),
        "lambda": round(float(model.lam), 6),
    }


def compare_models(results: list[dict]) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            "Method": r.get("method"),
            "N": r.get("n"),
            "R²": r.get("r_squared"),
            "AIC": r.get("aic"),
            "ρ (lag)": r.get("rho"),
            "λ (error)": r.get("lambda"),
        })
    return pd.DataFrame(rows)


def run_subgroup_ols(
    gdf: gpd.GeoDataFrame,
    dependent: str,
    covariates: list[str],
    group_col: str = "county_type",
    groups: list[str] | None = None,
) -> pd.DataFrame:
    """
    Run OLS separately for each subgroup and return a comparison DataFrame.

    Returns a long-format DataFrame with columns:
        group, n, r_squared, adj_r_squared, aic, variable, coef, p_value
    """
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools import add_constant

    if groups is None:
        groups = sorted(gdf[group_col].dropna().unique())

    rows = []
    for grp in groups:
        sub = gdf[gdf[group_col] == grp].copy()
        df = sub[[dependent] + covariates].dropna()
        if len(df) < 10:
            continue
        y = df[dependent]
        X = add_constant(df[covariates])
        model = OLS(y, X).fit(cov_type="HC3")

        base = {
            "group": grp,
            "n": int(model.nobs),
            "r_squared": round(float(model.rsquared), 4),
            "adj_r_squared": round(float(model.rsquared_adj), 4),
            "aic": round(float(model.aic), 2),
        }
        for var in model.params.index:
            rows.append({
                **base,
                "variable": str(var),
                "coef": round(float(model.params[var]), 6),
                "p_value": round(float(model.pvalues[var]), 6),
            })

    return pd.DataFrame(rows)


def population_coverage_analysis(
    gdf: gpd.GeoDataFrame,
    broadband_threshold: float = 0.65,
    population_col: str = "population",
) -> dict:
    """
    Compare two targeting strategies:
      A) LL-cluster tracts only (spatial market-failure signal)
      B) All tracts below broadband_threshold (needs-based)

    Returns metrics quantifying the guardrail tension: LL targeting misses
    generated population proxies outside the saved LL labels. No actual household counts or intervention effects are estimated.
    """
    underserved = gdf[gdf["broadband_rate"] < broadband_threshold].copy()
    total_underserved_hh = int(underserved[population_col].sum())

    # LL cluster tracts (must have run lisa_clusters first)
    if "lisa_cluster" not in gdf.columns:
        raise ValueError("Run lisa_clusters() before population_coverage_analysis().")

    ll_mask = gdf["lisa_cluster"] == "LL"
    ll_tracts = gdf[ll_mask].copy()
    ll_count = int(ll_mask.sum())

    # LL tracts that are also underserved
    ll_underserved = gdf[ll_mask & (gdf["broadband_rate"] < broadband_threshold)]
    ll_underserved_hh = int(ll_underserved[population_col].sum())

    # Missed: underserved but NOT in LL cluster
    missed = underserved[underserved["lisa_cluster"] != "LL"]
    missed_hh = int(missed[population_col].sum())

    # Coverage efficiency by county type
    coverage_by_type = {}
    if "county_type" in gdf.columns:
        for ct in sorted(gdf["county_type"].dropna().unique()):
            ct_under = underserved[underserved["county_type"] == ct]
            ct_ll = ll_underserved[ll_underserved["county_type"] == ct] if "county_type" in ll_underserved.columns else pd.DataFrame()
            total_hh = int(ct_under[population_col].sum())
            ll_hh = int(ct_ll[population_col].sum()) if len(ct_ll) > 0 else 0
            coverage_by_type[ct] = {
                "underserved_tracts": len(ct_under),
                "underserved_hh": total_hh,
                "ll_tracts": len(ct_ll),
                "ll_hh": ll_hh,
                "ll_coverage_pct": round(100 * ll_hh / total_hh, 1) if total_hh > 0 else 0.0,
            }

    ll_coverage_pct = round(100 * ll_underserved_hh / total_underserved_hh, 1) if total_underserved_hh > 0 else 0.0
    missed_pct = round(100 * missed_hh / total_underserved_hh, 1) if total_underserved_hh > 0 else 0.0

    return {
        "broadband_threshold": broadband_threshold,
        "total_underserved_tracts": len(underserved),
        "total_underserved_hh": total_underserved_hh,
        "ll_cluster_tracts": ll_count,
        "ll_underserved_tracts": len(ll_underserved),
        "ll_underserved_hh": ll_underserved_hh,
        "ll_coverage_pct": ll_coverage_pct,
        "missed_hh": missed_hh,
        "missed_pct": missed_pct,
        "coverage_by_type": coverage_by_type,
    }
