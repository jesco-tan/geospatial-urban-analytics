# Validation

I checked the corrected synthetic grid against an independently constructed PySAL lattice. Both queen and rook adjacency have one connected component, no islands, symmetric neighbour membership and cell IDs aligned with the data rows. All 16 Python tests passed.

I reran the spatial analysis with recorded seeds, two-sided local tests and Benjamini-Yekutieli adjustment. The summary and complete GeoJSON reproduced byte for byte before final figure-caption and whitespace changes. The current maps, targeting totals and explorer export are recorded in `outputs/run_summary.json` and `outputs/manifest.json`.

## Scope

These are generated cells and population proxies. The results do not establish measured household need, causal effects or subsidy eligibility. The queen/rook sensitivity is part of the result, and subgroup graphs can remain disconnected. See [REPORT.md](REPORT.md) for methods, interpretation and reproduction.
