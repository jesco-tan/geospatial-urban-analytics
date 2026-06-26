"""
Generate a self-contained HTML stakeholder report from run_summary.json and output PNGs.

Usage:
    python scripts/generate_html_report.py

Output:
    outputs/report.html , fully self-contained (no external dependencies)
"""

import json
import base64
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUTS = ROOT / "outputs"
SUMMARY_PATH = OUTPUTS / "run_summary.json"

CHART_DEFS = [
    ("exploratory_correlation.png", "Exploratory Analysis",
     "Distribution of broadband rates, income-broadband scatter (r = 0.713), and education-broadband scatter. "
     "The strong correlation confirms income is the dominant individual-level predictor, but substantial variance remains.",
     "blue"),
    ("broadband_distribution.png", "Broadband Rate Distribution by County Type",
     "KDE plots reveal structural heterogeneity: rural tracts concentrate below 0.40, suburban tracts span the threshold, "
     "and urban tracts are mostly well-served with a thin tail of affordability-suppressed outliers.",
     "blue"),
    ("moran_scatter.png", "Moran Scatter Plot, Global Moran's I = 0.914",
     "The steep positive slope (= Moran's I) confirms extreme spatial clustering. Points are coloured by LISA quadrant. "
     "LL cold spots (blue) cluster in the lower-left, low broadband with low-broadband neighbours.",
     "green"),
    ("lisa_cluster_map.png", "LISA Cold Spot / Hot Spot Map",
     "All 115 LL cold-spot tracts are rural (blue). All 95 HH hot-spot tracts are urban or suburban (red). "
     "Zero suburban or urban tracts form LL clusters, a critical finding for the guardrail analysis.",
     "green"),
    ("edi_by_cluster.png", "Secondary Outcome: Economic Disadvantage Index by LISA Cluster",
     "LL cold-spot tracts have median EDI = 0.838, the highest multi-dimensional deprivation of any cluster type. "
     "Infrastructure grants to LL tracts address income, education, and broadband deficits simultaneously.",
     "blue"),
    ("subgroup_regression.png", "Subgroup OLS: R² and Income Coefficient by County Type",
     "Rural OLS R² = 0.429 (highest); income coefficient in urban is 3.5× larger than rural (0.206 vs 0.059). "
     "Urban broadband is income-constrained, affordability is the binding driver, not infrastructure.",
     "amber"),
    ("regression_comparison.png", "Spatial Regression Model Comparison",
     "Spatial Lag outperforms OLS by 330 AIC points (−922 vs −592). ρ = 0.678 confirms direct spatial spillovers: "
     "a one-unit rise in neighbours' broadband raises own-tract adoption by 0.678 units.",
     "green"),
    ("guardrail_analysis.png", "Guardrail: LL-Cluster Targeting Misses 76.4% of Underserved Households",
     "CRITICAL: LL targeting covers only 23.6% of underserved households. Suburban (234,282 HH) and urban (68,250 HH) "
     "underserved populations receive zero coverage because their tracts do not form spatial clusters.",
     "red"),
]


def encode_image(path: Path) -> str:
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode()
    ext = path.suffix.lstrip(".").lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{data}"


ALERT_COLOURS = {
    "green": ("#d4edda", "#155724", "#c3e6cb"),
    "red": ("#f8d7da", "#721c24", "#f5c6cb"),
    "amber": ("#fff3cd", "#856404", "#ffeeba"),
    "blue": ("#cce5ff", "#004085", "#b8daff"),
}


def alert_box(colour: str, text: str) -> str:
    bg, fg, border = ALERT_COLOURS.get(colour, ALERT_COLOURS["blue"])
    return (
        f'<div style="background:{bg};color:{fg};border:1px solid {border};'
        f'border-radius:6px;padding:12px 16px;margin:12px 0;font-size:0.93rem">{text}</div>'
    )


def kpi_card(label: str, value: str, sub: str = "", colour: str = "#4472C4") -> str:
    return f"""
    <div style="background:white;border:1px solid #ddd;border-top:4px solid {colour};
                border-radius:6px;padding:18px 20px;min-width:180px;flex:1">
      <div style="font-size:0.8rem;color:#666;text-transform:uppercase;letter-spacing:0.05em">{label}</div>
      <div style="font-size:2rem;font-weight:700;color:{colour};margin:4px 0">{value}</div>
      <div style="font-size:0.82rem;color:#888">{sub}</div>
    </div>"""


def build_html(summary: dict) -> str:
    g_moran = summary.get("global_moran", {})
    guardrail = summary.get("guardrail", {})
    spatial_lag = summary.get("spatial_lag", {})
    ols = summary.get("ols_full", {})
    exploratory = summary.get("exploratory", {})

    # Navbar links
    nav_items = [
        ("#exploratory", "Exploratory"),
        ("#moran", "Moran's I"),
        ("#lisa", "LISA Clusters"),
        ("#edi", "EDI"),
        ("#subgroup", "Subgroup"),
        ("#regression", "Regression"),
        ("#guardrail", "Guardrail"),
        ("#decision", "Decision"),
    ]
    nav_links = " &nbsp;·&nbsp; ".join(
        f'<a href="{href}" style="color:#fff;text-decoration:none">{label}</a>'
        for href, label in nav_items
    )

    kpis = "".join([
        kpi_card("Global Moran's I", f"{g_moran.get('moran_i', 0):.3f}",
                 f"z = {g_moran.get('z_score', 0):.1f}, p < 0.001", "#2c7bb6"),
        kpi_card("Spatial Lag R²", f"{spatial_lag.get('r_squared', 0):.3f}",
                 f"ρ = {spatial_lag.get('rho', 0):.3f}, AIC {spatial_lag.get('aic', 0):.0f}", "#70AD47"),
        kpi_card("LL Cold Spots", str(summary.get("lisa_cluster_counts", {}).get("LL", 0)),
                 "tracts, all rural", "#d7191c"),
        kpi_card("Missed Households", f"{guardrail.get('missed_pct', 0):.0f}%",
                 f"{guardrail.get('missed_hh', 0):,} HH missed by LL targeting", "#ED7D31"),
    ])

    sections = []
    section_ids = ["exploratory", "moran", "lisa", "edi", "subgroup", "regression", "guardrail"]

    for i, (png_name, title, caption, colour) in enumerate(CHART_DEFS):
        img_src = encode_image(OUTPUTS / png_name)
        section_id = section_ids[i] if i < len(section_ids) else f"section-{i}"

        img_html = (
            f'<img src="{img_src}" alt="{title}" '
            f'style="width:100%;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.1)" />'
            if img_src else '<p style="color:#999">[Image not found]</p>'
        )

        sections.append(f"""
        <section id="{section_id}" style="margin-bottom:3rem">
          <h2 style="color:#1a1a2e;border-bottom:2px solid #4472C4;padding-bottom:6px">{title}</h2>
          {alert_box(colour, caption)}
          {img_html}
        </section>""")

    # Decision section
    missed_pct = guardrail.get("missed_pct", 0)
    ll_pct = guardrail.get("ll_coverage_pct", 0)
    decision_html = f"""
    <section id="decision" style="margin-bottom:3rem">
      <h2 style="color:#1a1a2e;border-bottom:2px solid #4472C4;padding-bottom:6px">Decision & Recommendation</h2>
      {alert_box("red",
        f"<b>Guardrail breach confirmed</b>: LL-cluster targeting covers only {ll_pct:.0f}% of underserved households. "
        f"A pure spatial rule misses {missed_pct:.0f}% of underserved people ({guardrail.get('missed_hh', 0):,} households)."
      )}
      {alert_box("green",
        "<b>Spatial Lag confirms market failure</b>: ρ = " + str(spatial_lag.get('rho', 0)) + ", AIC improvement of "
        + f"{(ols.get('aic', 0) - spatial_lag.get('aic', 0)):.0f}" + " points over OLS. Place-based infrastructure intervention is warranted in rural LL clusters."
      )}
      {alert_box("amber",
        "<b>Hybrid policy required</b>: Route BEAD infrastructure grants to all 115 LL rural cold-spot tracts. "
        "Route parallel affordability vouchers to suburban and urban tracts below the 65% broadband threshold."
      )}
      <table style="width:100%;border-collapse:collapse;margin-top:1rem;font-size:0.9rem">
        <thead>
          <tr style="background:#4472C4;color:white">
            <th style="padding:10px;text-align:left">Segment</th>
            <th style="padding:10px;text-align:left">Signal</th>
            <th style="padding:10px;text-align:left">Recommended Instrument</th>
          </tr>
        </thead>
        <tbody>
          <tr style="background:#f8f9fa">
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Rural LL cold spots (115 tracts)</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Spatial market failure, I_rural = 0.916</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6"><b>BEAD infrastructure grants</b></td>
          </tr>
          <tr>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Rural non-LL underserved (46 tracts)</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Low broadband, weak cluster signal</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Infrastructure grants (adjacency to LL zones)</td>
          </tr>
          <tr style="background:#f8f9fa">
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Suburban underserved (82 tracts)</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">Mixed signal, I_suburban = 0.592</td>
            <td style="padding:8px;border-bottom:1px solid #dee2e6">ISP construction incentive + affordability vouchers</td>
          </tr>
          <tr>
            <td style="padding:8px">Urban underserved (15 tracts)</td>
            <td style="padding:8px">Affordability-driven; income coef 3.5× rural</td>
            <td style="padding:8px"><b>Affordability vouchers + device + digital-skills</b></td>
          </tr>
        </tbody>
      </table>
    </section>"""

    all_sections = "\n".join(sections) + decision_html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>California BEAD Broadband Analysis, Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f7fa; color: #1a1a2e; line-height: 1.6; }}
    nav {{ position: sticky; top: 0; background: #1a1a2e; color: white;
           padding: 10px 24px; z-index: 1000; font-size: 0.85rem; }}
    .hero {{ background: linear-gradient(135deg, #1a1a2e 0%, #2c7bb6 100%);
             color: white; padding: 3rem 24px 2.5rem; }}
    .hero h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 0.4rem; }}
    .hero p {{ font-size: 1.05rem; opacity: 0.85; max-width: 720px; }}
    .kpi-strip {{ display: flex; gap: 1rem; flex-wrap: wrap;
                  background: #f0f4f8; padding: 1.5rem 24px; border-bottom: 1px solid #ddd; }}
    main {{ max-width: 960px; margin: 2rem auto; padding: 0 24px; }}
    h2 {{ font-size: 1.35rem; margin-bottom: 1rem; margin-top: 0.5rem; }}
    footer {{ text-align: center; padding: 2rem; color: #888; font-size: 0.82rem; }}
  </style>
</head>
<body>
  <nav>
    <b>BEAD Broadband Analysis</b> &nbsp;&nbsp;
    {nav_links}
  </nav>

  <div class="hero">
    <h1>California BEAD Broadband Subsidy Targeting</h1>
    <p>Spatial analysis of 400 census tracts: Moran's I = {g_moran.get('moran_i', 0):.3f},
       Spatial Lag R² = {spatial_lag.get('r_squared', 0):.3f}, LL cold spots = {summary.get('lisa_cluster_counts', {}).get('LL', 0)} tracts (all rural).
       Guardrail: LL-only targeting misses {missed_pct:.0f}% of underserved households.</p>
  </div>

  <div class="kpi-strip">
    {kpis}
  </div>

  <main>
    {all_sections}
  </main>

  <footer>
    Generated from <code>run_summary.json</code> · {summary.get('n_tracts', 0)} tracts ·
    Data: {summary.get('data_source', '')}
  </footer>
</body>
</html>"""


def main():
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(f"run_summary.json not found at {SUMMARY_PATH}. Run the notebook first.")

    summary = json.loads(SUMMARY_PATH.read_text())
    html = build_html(summary)
    out_path = OUTPUTS / "report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Generated: {out_path}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
