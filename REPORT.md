# Analyst Memo: California BEAD Broadband Subsidy Targeting
## Spatial Analysis of Broadband Equity, Run: 2026-06-24

---

## Executive Summary

Broadband adoption across California's 400 synthetic census tracts is one of the most spatially autocorrelated outcomes possible to measure: Global Moran's I = **0.914** (p < 0.001). Low-broadband tracts cluster next to other low-broadband tracts. The Spatial Lag model confirms this is not fully explained by income or education, the spatial coefficient ρ = **0.678** is large and significant, meaning a tract's expected broadband adoption rises by 0.68 percentage points for every one-percentage-point rise in its neighbours' adoption. This is the empirical signature of an infrastructure market failure: providers don't extend service into areas where adjacent demand is already weak.

**However, the policy recommendation is not "fund all LL clusters."** All 113 LISA cold-spot tracts are rural, and together they contain **119,165 households**: only **22.9%** of the 521,152 total underserved households. The remaining **401,987 underserved households (77.1%)** live in suburban and urban tracts that do not form spatial clusters. Their broadband gap is an affordability problem (income coefficient is 3.5× larger in urban areas than rural), not a supply market failure. Infrastructure grants are the wrong instrument for them; affordability vouchers are.

**Decision**: Implement a hybrid allocation. Route BEAD infrastructure grants to LL cold-spot tracts (all 113 rural tracts, covering ~55% of rural underserved households). Route parallel affordability subsidy to suburban and urban tracts below the 65% broadband threshold. A flat LL-only rule is empirically consistent but operationally wrong, it misses three in every four underserved households in California.

---

## 1. Data and Setup

**Source**: 400-tract synthetic GeoDataFrame structured to match California ACS 2022 patterns. The synthetic generator uses a shared latent "urban proximity" factor that drives income, education, and broadband through the same channel, ensuring OLS controls are genuinely informative. Spatial autocorrelation is planted via iterative box-blur on the broadband latent field.

**County type breakdown**: 161 rural tracts (40.3%), 107 suburban (26.8%), 132 urban (33.0%). Assigned by distance-decay from four synthetic urban centres mimicking SF Bay Area, LA metro, Sacramento, and San Diego.

**Broadband threshold**: 65%. Tracts below this threshold are classified as "underserved" and are the targeting population for BEAD funds.

- Underserved tracts: **258** (64.5% of all tracts)
- Underserved households: **521,152**

---

## 2. Exploratory Analysis

**Income-broadband correlation**: r = **0.713** (strong positive). Income is the single strongest predictor of broadband adoption. Education adds independent signal: r(education, broadband) = **0.571**.

**Distribution by county type** (median broadband rate):
- Rural: 0.274, majority of rural tracts are underserved
- Suburban: 0.598, near the threshold; distribution is wide
- Urban: 0.801, mostly well-served, but with a tail of suppressed low-income tracts

The right tail of rural broadband distribution is thin; almost all rural tracts fall below the 65% threshold. Urban tracts cluster above 0.75 but have a secondary concentration near 0.40–0.55 driven by the affordability-suppressed subset.

**Mechanistic interpretation**: The urban proximity factor drives all three outcomes, income, education, and infrastructure quality, through a shared channel. Within rural areas, all three are uniformly low. Within urban areas, income and education are high on average but infrastructure has already been extended (high broadband). The scattered urban low-broadband pockets are households that cannot afford service even where it exists.

---

## 3. Global Moran's I, Spatial Autocorrelation of Broadband

**Moran's I = 0.914** (expected = −0.003 under H0, z = 25.4, p_sim < 0.001 based on 999 permutations).

This is an extremely high autocorrelation coefficient. For context, I = 0.0 means random arrangement; I = 1.0 means perfect clustering. At 0.914, a tract's broadband rate is nearly perfectly predicted by its neighbours' broadband rates, geography is doing structural work that transcends the income and education controls.

**Mechanistic reason**: The synthetic data plants this via spatial smoothing of the latent broadband field, mimicking real-world mechanisms: provider coverage boundaries create sharp edges; terrain restricts cable or fibre runs; zoning creates uniformly rural or uniformly urban zones. These are geographic, not demographic.

**Subgroup Moran's I**:
| County Type | n | Moran's I | p_sim |
|---|---|---|---|
| Rural | 161 | **0.916** | < 0.001 |
| Suburban | 107 | **0.592** | < 0.001 |
| Urban | 132 | **0.325** | < 0.001 |

Rural I (0.916) nearly matches the global statistic, rural tracts are the dominant driver of spatial clustering. Urban I (0.325) is substantially lower: urban low-broadband tracts are geographically scattered, consistent with the hypothesis that urban broadband gaps are affordability-driven rather than spatially structured.

---

## 4. LISA Clusters, Cold Spot Detection

LISA (Local Moran's I) assigns each tract to a quadrant: HH (both tract and neighbours high), LL (both low), HL/LH (outlier), or NS (not significant at p < 0.05).

**Cluster counts**:
- **LL cold spots**: 113 tracts (28.3%), subsidy candidates under spatial targeting
- **HH hot spots**: 92 tracts (23.0%), already well-served, do not need infrastructure grants
- **LH outliers**: 4 tracts (1.0%), isolated low tracts surrounded by high-broadband neighbours
- **NS**: 191 tracts (47.8%)

**LISA breakdown by county type** (the critical finding):

| Cluster | Rural | Suburban | Urban |
|---|---|---|---|
| LL | **113** | 0 | 0 |
| HH | 0 | 2 | **90** |
| LH | 0 | 0 | 4 |
| NS | 48 | 105 | 38 |

**All 113 LL cold spots are rural. Zero suburban or urban tracts qualify as LL clusters.** This is not a modelling artefact, it reflects the spatial structure of the data. Urban low-broadband tracts are scattered across the urban grid (affordability problem: isolated pockets, not contiguous zones). Suburban tracts span the broadband range and don't cluster.

**Mechanistic reason**: LL clustering requires both a low-broadband tract AND low-broadband neighbours. Urban tracts have heterogeneous income and broadband, so the affordability-suppressed pockets are surrounded by high-broadband neighbours, they appear as LH outliers or NS, not LL. Rural tracts are uniformly low-access and densely connected in the spatial graph, producing large contiguous LL zones.

---

## 5. Secondary Outcome, Economic Disadvantage Index

The Economic Disadvantage Index (EDI) = 0.40×(1−income_norm) + 0.30×(1−education_norm) + 0.30×(1−broadband_norm). Higher = more disadvantaged.

**EDI by LISA cluster** (median):
- **LL cold spots**: EDI = **0.840**: highest multi-dimensional deprivation
- NS: EDI = 0.583
- LH outliers: EDI = 0.513
- HH hot spots: EDI = 0.385

**EDI by county type** (median):
- Rural: **0.818**
- Suburban: 0.574
- Urban: 0.409

LL cold spots are not only low-broadband, they compound low income and low education. This strengthens the case for prioritised investment: the spatial market failure hits precisely the tracts that are already most disadvantaged. Infrastructure grants to LL tracts address multiple deprivation dimensions simultaneously, not just the broadband gap.

---

## 6. Spatial Regression, OLS vs Spatial Lag vs Spatial Error

**OLS (full dataset)**:
- R² = **0.755**, Adj. R² = 0.753, AIC = **−592**
- log_income coefficient: **+0.208** (p < 0.001), a 1% rise in household income raises broadband rate by ~0.21 pp
- bach_rate coefficient: **+0.205** (p < 0.001), education rate and income are both independently significant
- log_population: **+0.129** (p < 0.001), denser tracts have higher broadband, controlling for income

**Spatial Lag (ML_Lag)**:
- R² = **0.911**, AIC = **−922**, ρ = **0.678**
- AIC improvement over OLS: **330 points**: overwhelming evidence that OLS is misspecified
- ρ = 0.678 means that after controlling for income, education, and population, a one-unit rise in neighbours' broadband raises own-tract broadband by 0.678 units, a very large direct spillover effect

**Spatial Error (ML_Error)**:
- R² = 0.712, AIC = **−797**, λ = **0.852**
- Also beats OLS by 205 AIC points; λ = 0.852 confirms spatially autocorrelated residuals even after including the covariates

**Best model**: Spatial Lag (AIC −922 vs −797 for Spatial Error). The Lag formulation fits better because the data-generating mechanism includes a direct broadband latent field smoothing step, neighbours' broadband directly influences each tract's broadband via shared infrastructure economics.

**Subgroup OLS R² and income coefficients**:
| County Type | R² | Income Coef | p |
|---|---|---|---|
| Rural | 0.429 | 0.059 | 0.002 |
| Suburban | 0.301 | 0.060 | < 0.001 |
| Urban | 0.323 | **0.206** | < 0.001 |

Two findings:
1. **R² is highest in rural (0.429)**: within rural areas, income variation tracks broadband well. But the global R² (0.755) is much higher because across all county types, the income gradient from rural to urban explains the bulk of the variance.
2. **Income coefficient is 3.5× larger in urban than rural**: in urban areas, a 1% income rise raises broadband by 0.21 pp, versus 0.06 pp in rural. This confirms that the urban broadband gap is primarily affordability-driven: income is the binding constraint for urban non-subscribers.

The urban OLS R² is lower than rural (0.323 vs 0.429) because the affordability-suppressed pockets introduce unexplained variance, some low-income urban tracts have even lower broadband than income alone would predict, due to compound barriers (cost, device availability, digital skills) that income doesn't fully capture.

---

## 7. Guardrail Analysis, Population Coverage

**Central question**: Does LL-cluster targeting reach most underserved households, or does it systematically miss some populations?

| Metric | Value |
|---|---|
| Total underserved tracts (broadband < 65%) | 258 |
| Total underserved households | 521,152 |
| LL cluster tracts | 113 |
| Underserved HH in LL tracts | 119,165 |
| **LL targeting coverage** | **22.9%** |
| **Households missed** | **401,987 (77.1%)** |

**Coverage by county type**:
| County Type | Underserved Tracts | Underserved HH | LL HH Covered | Coverage |
|---|---|---|---|---|
| Rural | 161 | 218,620 | 119,165 | **54.5%** |
| Suburban | 82 | 234,282 | 0 | **0%** |
| Urban | 15 | 68,250 | 0 | **0%** |

**This is the guardrail breach.** LL targeting covers 54.5% of rural underserved households, a respectable reach within rural zones. But it covers **zero** suburban and urban underserved households, because no suburban or urban tracts form LL clusters. Yet suburban underserved households (234,282) outnumber rural underserved households (218,620). And urban underserved (68,250) are concentrated in dense tracts where per-household subsidy cost is lowest.

**Mechanistic reason**: Suburban broadband is heterogeneous, some suburban tracts are well-served, some are not, so the spatial correlation is too mixed to produce LL clusters. Urban underserved tracts are isolated low-broadband pockets surrounded by high-broadband neighbours (affordability suppression without geographic spillover). Neither group forms LL clusters, but both groups contain large numbers of underserved people.

---

## 8. Disaggregated Recommendation

| Segment | Signal | Recommended Instrument |
|---|---|---|
| Rural LL cold spots (113 tracts) | Spatial market failure: ρ contribution dominant, I_rural = 0.916 | **BEAD infrastructure grants**: extend fibre/cable to unserved areas; each funded tract has multiplier effect on neighbours |
| Rural non-LL underserved (48 tracts) | Low broadband without strong cluster signal | Infrastructure grants to adjacent unserved zones; may benefit from LL spillover as network extends |
| Suburban underserved (82 tracts) | Mixed signal: I_suburban = 0.592, no LL clusters | **Hybrid**: targeted ISP incentive (lower-density areas may need construction subsidies) + affordability vouchers for income-eligible households |
| Urban underserved (15 tracts) | Affordability-driven; income coef 3.5× rural; no spatial clustering | **Affordability vouchers + device + digital-skills programmes**: infrastructure already exists, households can't subscribe |

---

## 9. Post-Analysis Monitoring Plan

If this analysis were applied to real ACS data and a subsidy programme was launched:

1. **18-month broadband re-survey**: Re-run the LISA analysis using updated ACS 1-year estimates. LL cold spots should dissolve (shrink in count) as funded tracts receive infrastructure. If LL count is unchanged after 18 months, the infrastructure grants have not reached take-up.

2. **EDI tracking**: Monitor EDI quarterly for funded tracts. The target is EDI declining in LL tracts, driven by broadband component rising. If income and education components also change (likely over longer time horizons), that confirms upstream spillover effects.

3. **Urban adoption rate vs. voucher deployment**: Track whether affordability vouchers in urban areas produce adoption rate increases proportional to income support. If not, digital skills or device availability is the binding constraint and the programme mix needs adjustment.

4. **Guardrail re-check**: Recalculate population coverage efficiency each year. Target: bring missed_pct below 50% by year 3 of the programme (from 77.1% today), and below 25% by year 5.

---

## Appendix: Synthetic Data vs Real Deployment

| Dimension | Synthetic Data | Real ACS Deployment |
|---|---|---|
| Tract geometry | 20×20 grid (perfect Queen contiguity) | Irregular tract boundaries; island tracts with zero neighbours (e.g., Channel Islands) |
| Spatial autocorrelation | Planted via box-blur (I ≈ 0.91) | Empirically estimated; California I typically 0.45–0.55 in ACS data |
| County type | Assigned by distance from synthetic urban centres | Must be inferred from county FIPS or Census Urban Area definitions |
| Guardrail suppressed tracts | 15 tracts, uniform mechanism | Real suppression is multidimensional (cost, device, language, literacy), less clean than synthetic |
| Income-broadband r | 0.713 | Typically 0.60–0.70 in CA ACS; direction and magnitude are realistic |
| Missing data | None (synthetic) | Real ACS has suppressed cells (small tracts), requiring imputation or exclusion |
| Spatial regression | Full weights matrix (no dropped tracts) | May need to subset W if tracts are dropped for missing data |
