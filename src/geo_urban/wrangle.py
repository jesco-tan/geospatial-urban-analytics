"""Geospatial wrangling: merge, reproject, derive features."""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd


def merge_acs_tiger(
    acs_df: pd.DataFrame,
    tiger_gdf: gpd.GeoDataFrame,
    projection_epsg: int = 3310,
    min_population: int = 500,
) -> gpd.GeoDataFrame:
    """Join ACS attributes onto TIGER geometry, reproject, derive features."""
    gdf = tiger_gdf[["GEOID", "geometry"]].merge(acs_df, on="GEOID", how="inner")
    gdf = gdf.to_crs(epsg=projection_epsg)
    gdf = gdf[gdf["population"] >= min_population].copy()
    gdf = _derive_features(gdf)
    return gdf


def _derive_features(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    if "broadband_subscriptions" in gdf.columns and "total_households_internet" in gdf.columns:
        gdf["broadband_rate"] = (
            gdf["broadband_subscriptions"] / gdf["total_households_internet"].replace(0, np.nan)
        ).clip(0, 1)

    if "bach_degree_plus" in gdf.columns and "total_pop_25plus" in gdf.columns:
        gdf["bach_rate"] = (
            gdf["bach_degree_plus"] / gdf["total_pop_25plus"].replace(0, np.nan)
        ).clip(0, 1)

    if "median_household_income" in gdf.columns:
        gdf["log_income"] = np.log1p(gdf["median_household_income"].clip(lower=1))

    if "population" in gdf.columns:
        gdf["log_population"] = np.log1p(gdf["population"])

    # Economic Disadvantage Index (real ACS data, no county_type available)
    if "median_household_income" in gdf.columns and "broadband_rate" in gdf.columns:
        inc = gdf["median_household_income"]
        inc_deficit = 1.0 - (inc - inc.min()) / (inc.max() - inc.min()).replace(0, 1)
        bb_deficit = 1.0 - gdf["broadband_rate"]
        if "bach_rate" in gdf.columns:
            edu = gdf["bach_rate"]
            edu_deficit = 1.0 - (edu - edu.min()) / (edu.max() - edu.min()).replace(0, 1)
            gdf["economic_disadvantage_index"] = (
                0.40 * inc_deficit + 0.30 * edu_deficit + 0.30 * bb_deficit
            ).clip(0, 1)
        else:
            gdf["economic_disadvantage_index"] = (
                0.55 * inc_deficit + 0.45 * bb_deficit
            ).clip(0, 1)

    key_cols = ["broadband_rate", "log_income", "bach_rate"]
    available = [c for c in key_cols if c in gdf.columns]
    gdf = gdf.dropna(subset=available)

    return gdf.reset_index(drop=True)


def area_km2(gdf: gpd.GeoDataFrame) -> pd.Series:
    """Return tract area in km²; assumes projected CRS in metres."""
    return gdf.geometry.area / 1e6
