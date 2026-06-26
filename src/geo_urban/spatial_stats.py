"""Spatial autocorrelation: Moran's I, LISA cluster detection, subgroup analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd


def build_weights(gdf: gpd.GeoDataFrame, queen: bool = True):
    """Build row-standardised spatial weights matrix (Queen or Rook contiguity)."""
    try:
        from libpysal.weights import Queen, Rook
        W = Queen.from_dataframe(gdf) if queen else Rook.from_dataframe(gdf)
        W.transform = "r"
        return W
    except ImportError:
        raise ImportError("libpysal is required. pip install libpysal")


def global_morans_i(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights,
    n_permutations: int = 999,
) -> dict:
    """Compute Global Moran's I with permutation-based pseudo p-value."""
    from esda.moran import Moran

    y = gdf[variable].values
    mi = Moran(y, weights, permutations=n_permutations)
    return {
        "moran_i": round(float(mi.I), 6),
        "expected_i": round(float(mi.EI), 6),
        "variance": round(float(mi.VI_norm), 8),
        "z_score": round(float(mi.z_norm), 4),
        "p_value_norm": round(float(mi.p_norm), 6),
        "p_value_sim": round(float(mi.p_sim), 6) if n_permutations > 0 else None,
        "n_permutations": n_permutations,
    }


def lisa_clusters(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights,
    significance: float = 0.05,
    n_permutations: int = 999,
) -> gpd.GeoDataFrame:
    """
    Compute Local Moran's I (LISA) and attach cluster labels.

    Labels: HH (broadband hot spot), LL (cold spot), HL/LH (outliers), NS (not significant).
    """
    from esda.moran import Moran_Local

    y = gdf[variable].values
    lm = Moran_Local(y, weights, permutations=n_permutations)

    gdf = gdf.copy()
    gdf["lisa_Is"] = lm.Is
    gdf["lisa_p_sim"] = lm.p_sim

    quad_map = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    labels = pd.Series(lm.q, dtype=int).map(quad_map).fillna("NS")
    labels[lm.p_sim >= significance] = "NS"
    gdf["lisa_cluster"] = labels.values

    return gdf


def subgroup_morans_i(
    gdf: gpd.GeoDataFrame,
    variable: str,
    group_col: str = "county_type",
    groups: list[str] | None = None,
    n_permutations: int = 999,
) -> pd.DataFrame:
    """
    Run Global Moran's I separately for each subgroup.

    Each subgroup gets its own contiguous weights matrix so the spatial
    autocorrelation measure is local to that zone, not contaminated by
    cross-zone borders.

    Returns a DataFrame with one row per group.
    """
    if groups is None:
        groups = sorted(gdf[group_col].dropna().unique())

    rows = []
    for grp in groups:
        sub = gdf[gdf[group_col] == grp].reset_index(drop=True).copy()
        if len(sub) < 5:
            continue
        try:
            W_sub = build_weights(sub, queen=True)
            result = global_morans_i(sub, variable, W_sub, n_permutations=n_permutations)
            rows.append({"group": grp, "n": len(sub), **result})
        except Exception as e:
            rows.append({"group": grp, "n": len(sub), "error": str(e)})

    return pd.DataFrame(rows)
