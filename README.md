# Synthetic broadband targeting: spatial analysis and an interactive explorer

Built spatial-analysis and Three.js exploration workflows for an artificial 400-cell grid. In the saved sample, LL targeting includes 22.9% of a defined underserved population proxy. Counts, geography and mechanisms are synthetic; the saved graph also has a documented contiguity limitation.

I built a spatial-analysis pipeline and interactive explorer to compare two targeting ideas: significant low-low clusters and all cells below a chosen adoption threshold. The published analysis uses 400 generated rectangles in an artificial 20 by 20 grid. They are not authentic Census tracts, and the counts are population proxies rather than observed California households.

The saved results illustrate the mechanics of spatial association, regression and targeting coverage. They do not diagnose actual market failure, establish subsidy eligibility or estimate policy effects.

## Read the results

[REPORT.md](REPORT.md) gives the supported results, assumptions and limitations. [report.html](outputs/report.html) contains the same interpretation with embedded figures. The [walkthrough notebook](notebooks/geo_walkthrough.ipynb) retains numerical evidence and corrected narrative. Modified code cells have cleared execution state until rerun. Old wording and reports are available through Git history.

No real users, customers, bank-disclosure measurements or policy effects are represented by this saved run.

## Reproduce or inspect

Render the current report without dependencies or analytical execution:

```powershell
python scripts/generate_html_report.py
```

Run the synthetic notebook in an isolated environment (this overwrites analytical outputs):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
# Install notebook tooling inside the same virtual environment if needed.
.venv/Scripts/python.exe -m pip install jupyter
.venv/Scripts/python.exe -m jupyter notebook notebooks/geo_walkthrough.ipynb
.venv/Scripts/python.exe -m pytest tests -q
```

The analytical requirements pin an older scientific stack. Use a compatible Python 3.11 virtual environment for the full notebook; Python 3.14 can render the report using the standard library without installing that stack.

## Evidence and implementation limits

Spatial-analysis workflow on a synthetic 400-cell grid, demonstrating Moran statistics, local patterns, spatial regression and population-proxy targeting comparisons.

See [REPORT.md](REPORT.md) for method definitions, saved-run provenance and remaining analytical limitations.
