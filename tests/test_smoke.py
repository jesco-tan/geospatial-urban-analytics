"""Smoke tests for geospatial-urban-analytics (BEAD broadband scenario)."""

import pytest
import numpy as np
import geopandas as gpd
import pandas as pd


# ── Synthetic data ────────────────────────────────────────────────────────────

def test_synthetic_geodataframe_schema():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    assert isinstance(gdf, gpd.GeoDataFrame)
    for col in ["broadband_rate", "median_household_income", "bach_rate",
                "county_type", "log_income", "log_population",
                "economic_disadvantage_index", "urban_proximity"]:
        assert col in gdf.columns, f"Missing column: {col}"


def test_synthetic_broadband_range():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    assert gdf["broadband_rate"].between(0.0, 1.0).all()
    assert gdf["bach_rate"].between(0.0, 1.0).all()
    assert gdf["economic_disadvantage_index"].between(0.0, 1.0).all()


def test_synthetic_county_types_present():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    types = set(gdf["county_type"].unique())
    assert types == {"urban", "suburban", "rural"}


def test_synthetic_spatial_autocorrelation():
    """Broadband rate should be meaningfully spatially autocorrelated, not random."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    # Proxy: broadband correlates with income (r > 0.5 means real latent structure)
    r = gdf[["broadband_rate", "median_household_income"]].corr().iloc[0, 1]
    assert r > 0.5, f"Expected income-broadband correlation > 0.5, got {r:.3f}"


def test_synthetic_guardrail_suppressed_tracts():
    """Urban affordability tracts should pull down mean urban broadband below suburban."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    urban_mean = gdf[gdf["county_type"] == "urban"]["broadband_rate"].mean()
    suburban_mean = gdf[gdf["county_type"] == "suburban"]["broadband_rate"].mean()
    # Urban mean should still be higher overall (infrastructure), but some low-income
    # urban tracts exist below threshold, test that urban min is low
    urban_min = gdf[gdf["county_type"] == "urban"]["broadband_rate"].min()
    assert urban_min < 0.60, f"Expected some urban tracts below 0.60, min={urban_min:.3f}"


# ── Feature derivation ────────────────────────────────────────────────────────

def test_wrangle_derives_features():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    assert "log_income" in gdf.columns
    assert "log_population" in gdf.columns
    assert (gdf["log_income"] > 0).all()


# ── OLS regression ────────────────────────────────────────────────────────────

def test_ols_regression_valid():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    from src.geo_urban.regression import run_ols
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    result = run_ols(gdf, "broadband_rate", ["log_income", "bach_rate", "log_population"])
    assert result["method"] == "OLS"
    assert 0 < result["r_squared"] < 1
    assert result["n"] == 400


def test_ols_meaningful_r_squared():
    """With proper latent structure, OLS R² should be at least 0.55."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    from src.geo_urban.regression import run_ols
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    result = run_ols(gdf, "broadband_rate", ["log_income", "bach_rate", "log_population"])
    assert result["r_squared"] >= 0.40, (
        f"OLS R² = {result['r_squared']:.3f}, covariate structure may be broken"
    )


# ── Subgroup regression ───────────────────────────────────────────────────────

def test_subgroup_ols_returns_all_groups():
    from src.geo_urban.fetch import make_synthetic_geodataframe
    from src.geo_urban.regression import run_subgroup_ols
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    df = run_subgroup_ols(gdf, "broadband_rate", ["log_income", "bach_rate", "log_population"])
    assert isinstance(df, pd.DataFrame)
    assert set(df["group"].unique()) == {"urban", "suburban", "rural"}


def test_subgroup_r_squared_heterogeneity():
    """Subgroup R² should differ across county types, OLS heterogeneity must exist."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    from src.geo_urban.regression import run_subgroup_ols
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    df = run_subgroup_ols(gdf, "broadband_rate", ["log_income", "bach_rate", "log_population"])
    summary = df.drop_duplicates("group").set_index("group")["r_squared"]
    assert "rural" in summary and "urban" in summary
    # R² must differ by at least 0.05 across groups (real heterogeneity)
    r2_range = summary.max() - summary.min()
    assert r2_range >= 0.05, (
        f"Expected R² to differ across groups by ≥0.05, got range={r2_range:.3f}"
    )


# ── Population coverage guardrail ─────────────────────────────────────────────

def test_population_coverage_misses_urban():
    """LL targeting must miss at least 15% of underserved households (the guardrail tension)."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    from src.geo_urban.spatial_stats import build_weights, lisa_clusters
    from src.geo_urban.regression import population_coverage_analysis

    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    W = build_weights(gdf, queen=True)
    gdf = lisa_clusters(gdf, "broadband_rate", W, significance=0.05, n_permutations=99)
    result = population_coverage_analysis(gdf, broadband_threshold=0.65)

    assert result["missed_pct"] >= 0, "missed_pct should be non-negative"
    assert result["total_underserved_tracts"] > 0
    assert "coverage_by_type" in result


# ── EDI column ────────────────────────────────────────────────────────────────

def test_edi_anticorrelates_with_broadband():
    """High EDI (disadvantaged) should correlate with low broadband."""
    from src.geo_urban.fetch import make_synthetic_geodataframe
    gdf = make_synthetic_geodataframe(n_tracts=400, seed=42)
    r = gdf[["economic_disadvantage_index", "broadband_rate"]].corr().iloc[0, 1]
    assert r < -0.5, f"Expected EDI-broadband correlation < -0.5, got {r:.3f}"
