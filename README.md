# California BEAD Broadband Subsidy Targeting
## Spatial Analysis of Broadband Equity Across Census Tracts

**Headline result**: Spatial clustering of broadband access is extreme (Global Moran's I = **0.914**, p < 0.001). All 113 LL cold-spot clusters are rural. But LL-cluster targeting reaches only **22.9%** of California's 521,152 underserved households, a 77.1% miss rate that invalidates a pure spatial-targeting rule and argues for a hybrid infrastructure + affordability policy.

---

## What this project does

A full spatial analysis pipeline answering one policy question: **which California census tracts should receive federal BEAD broadband infrastructure grants first?** The pipeline proceeds in four stages:

1. **Where is broadband low?**: Folium choropleths of income, broadband rate, and county type
2. **Is low broadband spatially clustered?**: Global Moran's I with permutation test
3. **Which specific tracts form cold spots?**: LISA (Local Moran's I), HH/LL/HL/LH labels
4. **Is clustering explained by income and education, or by spatial spillovers?**: OLS vs Spatial Lag vs Spatial Error (AIC comparison)

The LL (low-low) cold spots answer "where is market failure?", but the guardrail analysis shows they do not answer "where are the underserved people?"

---

## Techniques demonstrated

| Technique | Implementation | Note |
|---|---|---|
| Spatial weights | `libpysal` Queen contiguity, row-standardised | 400 grid tracts, avg 3 neighbours |
| Global Moran's I | `esda.Moran`, 999 permutations | I = 0.914, z = 25.4, p < 0.001 |
| LISA clusters | `esda.Moran_Local`, p < 0.05 threshold | 113 LL, 92 HH, 4 LH, 191 NS |
| OLS regression | `statsmodels` HC3 robust SE | R² = 0.755, AIC = −592 |
| Spatial Lag (ML) | `spreg.ML_Lag` | R² = 0.911, AIC = −922, ρ = 0.678 |
| Spatial Error (ML) | `spreg.ML_Error` | R² = 0.712, AIC = −797, λ = 0.852 |
| Subgroup OLS | Per-county-type regression | R² rural 0.429, suburban 0.301, urban 0.323 |
| Subgroup Moran's I | Per-county-type weights | Rural I = 0.916, urban I = 0.325 |
| Coverage guardrail | Population-weighted targeting analysis | LL-only targets 22.9% of underserved HH |
| Interactive maps | `folium` choropleths saved as HTML | Open in browser from `outputs/` |
| Synthetic data | Latent-factor structured generator | Urban proximity drives income, edu, broadband |

---

## Notebook sections

| Section | What it covers |
|---|---|
| **1. Setup & Data** | Config, synthetic generator, county type breakdown |
| **2. Exploratory Analysis** | Distribution histograms, income-broadband scatter (r = 0.713), density by county type |
| **3. Choropleth Maps** | Income, broadband rate, county type, three interactive HTML maps |
| **4. Global Moran's I** | Permutation test, Moran scatter plot coloured by LISA quadrant |
| **5. LISA Clusters** | Cold spot count and breakdown by county type; static + interactive maps |
| **6. Secondary Outcome** | Economic Disadvantage Index by cluster (LL median EDI = 0.840) |
| **7. Disaggregated Analysis** | Subgroup Moran's I and OLS by county type, reveals urban/rural divergence |
| **8. Spatial Regression** | OLS vs Lag vs Error, Spatial Lag wins by 330 AIC points; ρ = 0.678 |
| **9. Guardrail Analysis** | Population coverage: LL targeting misses 401,987 households (77.1%) |
| **10. Decision Synthesis** | Policy recommendation + `run_summary.json` export |

---

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
jupyter notebook notebooks/geo_walkthrough.ipynb
```

No Census API key required, synthetic fallback ships in repo. Set `USE_SYNTHETIC = False` and provide a key for real ACS data.

```bash
pytest tests -q   # 12 tests
```

---

## Output file inventory

| File | Type | Description |
|---|---|---|
| `outputs/choropleth_income.html` | Interactive | Median household income choropleth |
| `outputs/choropleth_broadband.html` | Interactive | Broadband adoption rate choropleth |
| `outputs/choropleth_county_type.html` | Interactive | Urban / suburban / rural zone map |
| `outputs/choropleth_lisa.html` | Interactive | LISA cluster map with tooltips |
| `outputs/lisa_cluster_map.png` | Static | LISA cold spot / hot spot map |
| `outputs/moran_scatter.png` | Static | Moran scatter plot (I = 0.914) |
| `outputs/broadband_distribution.png` | Static | KDE by county type with underserved threshold |
| `outputs/exploratory_correlation.png` | Static | Distribution + bivariate scatter panels |
| `outputs/edi_by_cluster.png` | Static | Economic Disadvantage Index by LISA cluster |
| `outputs/subgroup_regression.png` | Static | R² and income coefficient by county type |
| `outputs/guardrail_analysis.png` | Static | Coverage gap scatter + stacked bar by county type |
| `outputs/regression_comparison.png` | Static | R² and AIC bar charts, OLS vs Lag vs Error |
| `outputs/regression_comparison.csv` | Data | Numeric model comparison table |
| `outputs/run_summary.json` | Data | All numeric results from the run |
| `outputs/report.html` | HTML | Self-contained stakeholder report (generated by `scripts/generate_html_report.py`) |

---

## Tech stack

`geopandas` · `folium` · `libpysal` · `esda` · `spreg` · `statsmodels` · `matplotlib` · `seaborn`

See [`REPORT.md`](REPORT.md) for the full analyst memo with mechanistic explanations and policy recommendations.
