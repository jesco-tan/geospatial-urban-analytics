"""Spatial autocorrelation: Moran's I, LISA cluster detection, subgroup analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd


def build_weights(gdf: gpd.GeoDataFrame, queen: bool = True):
    """Build row-standardised spatial weights matrix (Queen or Rook contiguity)."""
    from libpysal.weights import W, Queen, Rook
    if {"grid_row", "grid_col"}.issubset(gdf.columns):
        ids = gdf["GEOID"].tolist()
        coords = list(zip(gdf.grid_row, gdf.grid_col))
        if len(set(coords)) != len(coords) or len(set(ids)) != len(ids):
            raise ValueError("Grid coordinates and IDs must be unique")
        lookup = dict(zip(coords, ids))
        offsets = [(r, c) for r in (-1, 0, 1) for c in (-1, 0, 1)
                   if (r or c) and (queen or abs(r) + abs(c) == 1)]
        neighbors = {id_: [lookup[(r+dr,c+dc)] for dr,dc in offsets
                          if (r+dr,c+dc) in lookup]
                     for id_,(r,c) in zip(ids,coords)}
        weights = W(neighbors, id_order=ids)
    else:
        weights = (Queen if queen else Rook).from_dataframe(gdf, use_index=True)
    weights.transform = "r"
    return weights


def global_morans_i(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights,
    n_permutations: int = 999,
    seed: int = 42,
) -> dict:
    """Compute Global Moran's I with permutation-based pseudo p-value."""
    from esda.moran import Moran

    y = gdf[variable].values
    np.random.seed(seed)
    mi = Moran(y, weights, permutations=n_permutations)
    return {
        "moran_i": round(float(mi.I), 6),
        "expected_i": round(float(mi.EI), 6),
        "variance": round(float(mi.VI_norm), 8),
        "z_score": round(float(mi.z_norm), 4),
        "p_value_norm": round(float(mi.p_norm), 6),
        "p_value_sim": round(min(1.0, 2 * float(mi.p_sim)), 6) if n_permutations > 0 else None,
        "n_permutations": n_permutations,
    }


def lisa_clusters(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights,
    significance: float = 0.05,
    n_permutations: int = 999,
    seed: int = 42,
    correction: str = "fdr_by",
) -> gpd.GeoDataFrame:
    """
    Compute Local Moran's I (LISA) and attach cluster labels.

    Labels: HH (broadband hot spot), LL (cold spot), HL/LH (outliers), NS (not significant).
    """
    from esda.moran import Moran_Local

    y = gdf[variable].values
    lm = Moran_Local(y, weights, permutations=n_permutations, seed=seed, n_jobs=1, alternative="directed")

    gdf = gdf.copy()
    gdf["lisa_Is"] = lm.Is
    p_two = np.minimum(1.0, 2 * lm.p_sim)
    gdf["lisa_p_sim"] = p_two

    quad_map = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
    labels = pd.Series(lm.q, dtype=int).map(quad_map).fillna("NS")
    gdf["lisa_cluster_raw"] = np.where(p_two < significance, labels, "NS")
    from statsmodels.stats.multitest import multipletests
    if correction not in ("fdr_by", "none"):
        raise ValueError("Use fdr_by or none")
    adjusted = multipletests(p_two, method="fdr_by")[1] if correction == "fdr_by" else p_two
    gdf["lisa_p_adjusted"] = adjusted
    labels[adjusted >= significance] = "NS"
    gdf["lisa_cluster"] = labels.values

    return gdf


def subgroup_morans_i(
    gdf: gpd.GeoDataFrame,
    variable: str,
    group_col: str = "county_type",
    groups: list[str] | None = None,
    n_permutations: int = 999,
    seed: int = 42,
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
