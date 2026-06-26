"""Download Census ACS data and TIGER shapefiles."""

from __future__ import annotations

import numpy as np
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path


CENSUS_API = "https://api.census.gov/data"


def fetch_acs_data(
    state_fips: str,
    variables: dict[str, str],
    year: int = 2022,
    geometry_level: str = "tract",
    census_api_key: str | None = None,
) -> pd.DataFrame:
    """Pull ACS 5-year estimates from the Census Bureau API."""
    var_codes = list(variables.values())
    var_str = "NAME," + ",".join(var_codes)

    if geometry_level == "tract":
        geo = f"for=tract:*&in=state:{state_fips}&in=county:*"
    elif geometry_level == "county":
        geo = f"for=county:*&in=state:{state_fips}"
    else:
        geo = f"for=block+group:*&in=state:{state_fips}&in=county:*&in=tract:*"

    url = f"{CENSUS_API}/{year}/acs/acs5?get={var_str}&{geo}"
    if census_api_key:
        url += f"&key={census_api_key}"

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    cols = data[0]
    df = pd.DataFrame(data[1:], columns=cols)

    if geometry_level == "tract":
        df["GEOID"] = df["state"] + df["county"] + df["tract"]
        df = df.drop(columns=["state", "county", "tract", "NAME"])
    elif geometry_level == "county":
        df["GEOID"] = df["state"] + df["county"]
        df = df.drop(columns=["state", "county", "NAME"])

    rev = {v: k for k, v in variables.items()}
    df = df.rename(columns=rev)
    for col in variables.keys():
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_tiger_shapefile(
    state_fips: str,
    year: int = 2022,
    geometry_level: str = "tract",
    cache_dir: Path | None = None,
) -> gpd.GeoDataFrame:
    """Download TIGER/Line shapefile from Census and return as GeoDataFrame."""
    if cache_dir is None:
        cache_dir = Path("data") / "shapefiles"
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    if geometry_level == "tract":
        fname = f"tl_{year}_{state_fips}_tract"
        url = f"https://www2.census.gov/geo/tiger/TIGER{year}/TRACT/{fname}.zip"
    elif geometry_level == "county":
        fname = f"tl_{year}_{state_fips}_county"
        url = f"https://www2.census.gov/geo/tiger/TIGER{year}/COUNTY/{fname}.zip"
    else:
        raise ValueError(f"geometry_level {geometry_level!r} not supported")

    zip_path = cache_dir / f"{fname}.zip"
    if not zip_path.exists():
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)

    gdf = gpd.read_file(f"zip://{zip_path}")
    gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11 if geometry_level == "tract" else 5)
    return gdf


def _spatial_smooth(grid: np.ndarray, iterations: int = 3) -> np.ndarray:
    """Apply iterative 3×3 box blur to a 2D grid (creates spatial autocorrelation)."""
    g = grid.copy().astype(float)
    nrows, ncols = g.shape
    for _ in range(iterations):
        padded = np.pad(g, 1, mode="edge")
        smoothed = np.zeros_like(g)
        for di in range(-1, 2):
            for dj in range(-1, 2):
                smoothed += padded[1 + di : nrows + 1 + di, 1 + dj : ncols + 1 + dj]
        g = smoothed / 9.0
    return g


def make_synthetic_geodataframe(n_tracts: int = 400, seed: int = 42) -> gpd.GeoDataFrame:
    """
    Build a spatially-structured synthetic GeoDataFrame for the California BEAD
    broadband subsidy analysis.

    Design:
    - Grid geometry (20×20) ensures proper Queen contiguity for libpysal.
    - A shared latent "urban proximity" factor drives income, education, AND
      broadband through the same channel, OLS controls genuinely explain variance
      and CUSUM/LISA tests are non-trivial.
    - Spatial autocorrelation is planted via iterative box-blur on the broadband
      latent field, not incidental.
    - Guardrail tension: 15 dense low-income urban tracts receive reduced broadband
      rates (affordability problem, not spatial market failure) so LL-cluster
      targeting alone misses a significant share of underserved households.
    """
    from shapely.geometry import box

    rng = np.random.default_rng(seed)

    # ── Grid geometry ─────────────────────────────────────────────────────────────
    ncols, nrows = 20, 20
    assert ncols * nrows == n_tracts, "n_tracts must equal ncols*nrows (default 400)"

    # Approximate California bounding box (WGS84)
    lon_min, lon_max = -124.5, -114.0
    lat_min, lat_max = 32.5, 42.0
    cell_w = (lon_max - lon_min) / ncols
    cell_h = (lat_max - lat_min) / nrows

    geoids, geometries, col_idxs, row_idxs = [], [], [], []
    for r in range(nrows):
        for c in range(ncols):
            lon0 = lon_min + c * cell_w
            lat0 = lat_min + r * cell_h
            geometries.append(box(lon0, lat0, lon0 + cell_w, lat0 + cell_h))
            geoids.append(f"06{r * ncols + c:07d}")
            col_idxs.append(c)
            row_idxs.append(r)

    col_arr = np.array(col_idxs)
    row_arr = np.array(row_idxs)
    col_norm = col_arr / (ncols - 1)
    row_norm = row_arr / (nrows - 1)

    # ── Urban proximity latent factor ─────────────────────────────────────────────
    # Four urban centres positioned to mimic SF Bay, LA metro, Sacramento, San Diego.
    # Coordinates are in normalised [0,1] grid space: (col_norm, row_norm).
    #   col_norm 0 = far west (ocean side), 1 = east
    #   row_norm 0 = south (San Diego), 1 = north (Eureka)
    urban_centers = [
        (0.20, 0.72),   # SF Bay Area
        (0.38, 0.30),   # LA metro
        (0.40, 0.75),   # Sacramento
        (0.32, 0.12),   # San Diego
    ]

    raw_prox = np.zeros(n_tracts)
    for cx, cy in urban_centers:
        dist = np.sqrt((col_norm - cx) ** 2 + (row_norm - cy) ** 2)
        raw_prox = np.maximum(raw_prox, np.exp(-dist / 0.20))

    # Smooth urban proximity to give gradual transitions
    prox_grid = np.zeros((nrows, ncols))
    for i in range(n_tracts):
        prox_grid[row_arr[i], col_arr[i]] = raw_prox[i]
    prox_grid = _spatial_smooth(prox_grid, iterations=4)
    urban_proximity = np.array([prox_grid[row_arr[i], col_arr[i]] for i in range(n_tracts)])
    urban_proximity = (urban_proximity - urban_proximity.min()) / (
        urban_proximity.max() - urban_proximity.min()
    )

    # ── County type (disaggregation dimension) ────────────────────────────────────
    county_type = np.where(
        urban_proximity > 0.62, "urban",
        np.where(urban_proximity > 0.35, "suburban", "rural"),
    )

    # ── Covariates from shared latent factor ──────────────────────────────────────
    # Income: log-normal. Rural mu ≈ log($34k), urban mu ≈ log($95k).
    income_mu = 10.4 + 1.05 * urban_proximity
    income = rng.lognormal(mean=income_mu, sigma=0.32).astype(int).clip(15_000, 300_000)

    # Education: beta, rate rises with urban proximity.
    bach_a = (1.8 + 4.2 * urban_proximity + rng.normal(0, 0.25, n_tracts)).clip(0.5)
    bach_b = (5.5 - 2.5 * urban_proximity + rng.normal(0, 0.25, n_tracts)).clip(0.8)
    bach_rate = rng.beta(bach_a, bach_b).clip(0.02, 0.85)

    # Population: negative binomial, denser near urban centres.
    pop_mu = 600 + 5200 * urban_proximity
    pop_r = 5
    pop_p = pop_r / (pop_mu + pop_r)
    population = rng.negative_binomial(pop_r, pop_p).clip(100).astype(int)

    # ── Broadband rate (primary outcome) ─────────────────────────────────────────
    # Three genuine channels through latent factor:
    #   infrastructure quality (urban_proximity), income, education.
    # Spatial autocorrelation added by smoothing the broadband latent field.
    income_norm = (income - income.min()) / (income.max() - income.min())

    bb_latent = (
        0.38 * urban_proximity
        + 0.30 * income_norm
        + 0.12 * bach_rate
        + 0.20 * rng.normal(0, 0.06, n_tracts)
    )

    bb_grid = np.zeros((nrows, ncols))
    for i in range(n_tracts):
        bb_grid[row_arr[i], col_arr[i]] = bb_latent[i]
    bb_grid = _spatial_smooth(bb_grid, iterations=3)
    bb_latent = np.array([bb_grid[row_arr[i], col_arr[i]] for i in range(n_tracts)])

    # Map to realistic CA broadband range [0.18, 0.96]
    bb_norm = (bb_latent - bb_latent.min()) / (bb_latent.max() - bb_latent.min())
    broadband_rate = 0.18 + 0.78 * bb_norm

    # ── Guardrail tension: urban affordability tracts ─────────────────────────────
    # 15 high-population, low-income urban tracts receive suppressed broadband:
    # affordability problem, not infrastructure gap. They will NOT form LL clusters
    # but DO contain a disproportionate share of underserved households, breaking
    # the assumption that LL-cluster targeting covers all underserved populations.
    urban_mask = county_type == "urban"
    income_p40_urban = np.percentile(income[urban_mask], 40)
    candidates = np.where(urban_mask & (income < income_p40_urban))[0]
    if len(candidates) >= 15:
        suppress_idx = rng.choice(candidates, size=15, replace=False)
        broadband_rate[suppress_idx] *= rng.uniform(0.52, 0.72, size=15)

    broadband_rate = broadband_rate.clip(0.12, 0.96)

    # ── Derived features ──────────────────────────────────────────────────────────
    log_income = np.log1p(income.astype(float))
    log_population = np.log1p(population.astype(float))

    # Economic Disadvantage Index: composite of normalised deficits
    inc_deficit = 1.0 - income_norm
    edu_deficit = 1.0 - (bach_rate - bach_rate.min()) / (bach_rate.max() - bach_rate.min())
    bb_deficit = 1.0 - bb_norm
    economic_disadvantage_index = (0.40 * inc_deficit + 0.30 * edu_deficit + 0.30 * bb_deficit).clip(0, 1)

    gdf = gpd.GeoDataFrame(
        {
            "GEOID": geoids,
            "geometry": geometries,
            "median_household_income": income,
            "broadband_rate": broadband_rate,
            "population": population,
            "bach_rate": np.round(bach_rate, 4),
            "county_type": county_type,
            "urban_proximity": np.round(urban_proximity, 4),
            "log_income": np.round(log_income, 4),
            "log_population": np.round(log_population, 4),
            "economic_disadvantage_index": np.round(economic_disadvantage_index, 4),
        },
        crs="EPSG:4326",
    )

    return gdf
