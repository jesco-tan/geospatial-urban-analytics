# Broadband targeting on a verified synthetic grid

A spatial workflow on 400 artificial cells with deterministic queen and rook neighbours, seeded local inference and BY multiplicity adjustment. Primary LL targeting includes 16.5% of the defined underserved population proxy. Rook sensitivity includes 2.5%. These are synthetic results, not measured policy outcomes.

See [REPORT.md](REPORT.md), [manifest](outputs/manifest.json) and [validation](VALIDATION.md).

## Reproduce

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/run_analysis.py
python scripts/generate_html_report.py
```

Pinned for Python 3.14 on Windows. Numerical tolerance is documented in the manifest. The notebook invokes the same runner. The companion explorer loads the hash-verified v2 export; hosted publication is a separate step.
