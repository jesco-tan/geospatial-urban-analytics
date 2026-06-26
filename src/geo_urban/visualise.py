"""Static chart helpers, Matplotlib/Seaborn."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import geopandas as gpd
from pathlib import Path

sns.set_theme(style="whitegrid", font_scale=1.05)

CLUSTER_COLOURS = {
    "HH": "#d7191c",
    "LL": "#2c7bb6",
    "HL": "#fdae61",
    "LH": "#abd9e9",
    "NS": "#cccccc",
}

COUNTY_PALETTE = {
    "urban": "#5e3c99",
    "suburban": "#b2abd2",
    "rural": "#fdb863",
}


def plot_lisa_static(gdf: gpd.GeoDataFrame, save_path: Path | None = None) -> plt.Figure:
    """Static LISA cluster choropleth."""
    fig, ax = plt.subplots(figsize=(12, 10))
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    colours = gdf_wgs84["lisa_cluster"].map(CLUSTER_COLOURS).fillna("#cccccc")
    gdf_wgs84.plot(color=colours, linewidth=0.1, edgecolor="white", ax=ax)
    patches = [mpatches.Patch(color=v, label=k) for k, v in CLUSTER_COLOURS.items()]
    ax.legend(handles=patches, loc="lower left", title="LISA Cluster", fontsize=9)
    ax.set_title("LISA Broadband Clusters, California Census Tracts\n(LL cold spots = market-failure candidates for BEAD subsidy)", fontsize=13)
    ax.axis("off")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_moran_scatter(
    gdf: gpd.GeoDataFrame,
    variable: str,
    weights,
    moran_i: float,
    p_value: float,
    save_path: Path | None = None,
) -> plt.Figure:
    """Moran scatter plot (standardised variable vs spatial lag)."""
    import libpysal

    y = gdf[variable].values
    y_std = (y - y.mean()) / y.std()
    lag_y = libpysal.weights.lag_spatial(weights, y_std)

    colours = gdf["lisa_cluster"].map(CLUSTER_COLOURS).fillna("#cccccc") if "lisa_cluster" in gdf.columns else "#4472C4"

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_std, lag_y, alpha=0.5, s=14, c=colours, linewidths=0)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.axvline(0, color="grey", linewidth=0.8, linestyle="--")

    m, b = np.polyfit(y_std, lag_y, 1)
    xs = np.linspace(y_std.min(), y_std.max(), 100)
    ax.plot(xs, m * xs + b, color="red", linewidth=1.8, label=f"slope = {m:.4f}")

    ax.set_xlabel(f"Standardised {variable}", fontsize=11)
    ax.set_ylabel(f"Spatial Lag of Standardised {variable}", fontsize=11)
    ax.set_title(
        f"Moran Scatter Plot, {variable}\n"
        f"Global Moran's I = {moran_i:.4f}   (p_sim = {p_value:.4f})",
        fontsize=12,
    )

    if "lisa_cluster" in gdf.columns:
        patches = [mpatches.Patch(color=v, label=k) for k, v in CLUSTER_COLOURS.items()]
        ax.legend(handles=patches, fontsize=8, title="LISA", loc="upper left")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_regression_comparison(comparison_df: pd.DataFrame, save_path: Path | None = None) -> plt.Figure:
    df = comparison_df.dropna(subset=["AIC"])
    colours = ["#4472C4", "#ED7D31", "#70AD47"][: len(df)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    axes[0].bar(df["Method"], df["R²"], color=colours)
    axes[0].set_title("Pseudo-R² by Model", fontsize=12)
    axes[0].set_ylabel("R²")
    axes[0].set_ylim(0, 1)
    for i, (_, row) in enumerate(df.iterrows()):
        if pd.notna(row["R²"]):
            axes[0].text(i, row["R²"] + 0.01, f"{row['R²']:.3f}", ha="center", fontsize=9)

    axes[1].bar(df["Method"], df["AIC"], color=colours)
    axes[1].set_title("AIC by Model (lower = better fit)", fontsize=12)
    axes[1].set_ylabel("AIC")
    best_aic = df["AIC"].min()
    for i, (_, row) in enumerate(df.iterrows()):
        if pd.notna(row["AIC"]):
            marker = " ✓" if row["AIC"] == best_aic else ""
            axes[1].text(i, row["AIC"] + abs(best_aic) * 0.005, f"{row['AIC']:.0f}{marker}", ha="center", fontsize=9)

    plt.suptitle("Spatial Regression Model Comparison, Broadband Rate", fontsize=13, y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_broadband_distribution(
    gdf: gpd.GeoDataFrame,
    broadband_threshold: float = 0.65,
    save_path: Path | None = None,
) -> plt.Figure:
    """Distribution of broadband rates by county type, shows the heterogeneous gap."""
    fig, ax = plt.subplots(figsize=(9, 5))

    order = ["rural", "suburban", "urban"]
    order = [g for g in order if g in gdf["county_type"].values]

    for ct in order:
        sub = gdf[gdf["county_type"] == ct]["broadband_rate"].dropna()
        sns.kdeplot(sub, ax=ax, label=ct.capitalize(), color=COUNTY_PALETTE.get(ct, "#888888"),
                    fill=True, alpha=0.30, linewidth=2)

    ax.axvline(broadband_threshold, color="red", linewidth=1.5, linestyle="--",
               label=f"Underserved threshold ({broadband_threshold:.0%})")

    ax.set_xlabel("Broadband Adoption Rate", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.set_title(
        "Broadband Rate Distribution by County Type\n"
        "Rural and suburban tracts have heavier left tails, but urban poor tracts are scattered",
        fontsize=12,
    )
    ax.legend(fontsize=10)
    ax.set_xlim(0, 1)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_subgroup_regression(
    subgroup_df: pd.DataFrame,
    save_path: Path | None = None,
) -> plt.Figure:
    """
    Forest-plot style: R² by county type plus coefficient comparison.
    Shows that OLS explains rural broadband poorly (R² lower, spatial spillovers dominate).
    """
    summary = subgroup_df.drop_duplicates(subset=["group"])[["group", "r_squared", "n", "aic"]].copy()
    order = ["rural", "suburban", "urban"]
    summary["group"] = pd.Categorical(summary["group"], categories=order, ordered=True)
    summary = summary.sort_values("group")

    coef_vars = [v for v in subgroup_df["variable"].unique() if v != "const"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel 1: R² by group
    colours = [COUNTY_PALETTE.get(g, "#888") for g in summary["group"]]
    bars = axes[0].barh(summary["group"], summary["r_squared"], color=colours, edgecolor="white")
    for bar, (_, row) in zip(bars, summary.iterrows()):
        axes[0].text(
            row["r_squared"] + 0.005, bar.get_y() + bar.get_height() / 2,
            f"R²={row['r_squared']:.3f}  (n={int(row['n'])})",
            va="center", fontsize=9,
        )
    axes[0].set_xlabel("OLS R²", fontsize=11)
    axes[0].set_title("OLS Explanatory Power by County Type\n(lower urban R² = affordability factors income alone cannot explain)", fontsize=11)
    axes[0].set_xlim(0, 1)

    # Panel 2: log_income coefficient comparison (the main covariate)
    coef_income = subgroup_df[subgroup_df["variable"] == "log_income"].copy()
    if not coef_income.empty:
        coef_income["group"] = pd.Categorical(coef_income["group"], categories=order, ordered=True)
        coef_income = coef_income.sort_values("group")
        colours2 = [COUNTY_PALETTE.get(g, "#888") for g in coef_income["group"]]
        axes[1].barh(coef_income["group"], coef_income["coef"], color=colours2, edgecolor="white")
        for _, row in coef_income.iterrows():
            pstar = "***" if row["p_value"] < 0.001 else "**" if row["p_value"] < 0.01 else "*" if row["p_value"] < 0.05 else "ns"
            axes[1].text(
                row["coef"] + 0.0005,
                list(order).index(row["group"]),
                f"{row['coef']:.4f} {pstar}",
                va="center", fontsize=9,
            )
        axes[1].axvline(0, color="grey", linewidth=0.8, linestyle="--")
        axes[1].set_xlabel("OLS Coefficient (log_income → broadband_rate)", fontsize=11)
        axes[1].set_title("Income Effect on Broadband by County Type\n(income coefficient strongest in rural; urban has suppressed tracts income can't explain)", fontsize=11)

    plt.suptitle("Subgroup OLS: Rural Broadband Well-Explained by Income; Urban Has a Residual Gap", fontsize=13, y=1.02)
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_guardrail(
    gdf: gpd.GeoDataFrame,
    coverage_result: dict,
    broadband_threshold: float = 0.65,
    save_path: Path | None = None,
) -> plt.Figure:
    """
    The analytical tension visualised: LL-cluster targeting misses urban underserved.

    Panel 1: scatter of underserved tracts, population vs broadband rate,
             coloured by LL cluster membership and county type.
    Panel 2: stacked bar of household coverage by county type, shows the gap.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Panel 1: scatter
    underserved = gdf[gdf["broadband_rate"] < broadband_threshold].copy()
    is_ll = underserved["lisa_cluster"] == "LL"

    scatter_colours = underserved["county_type"].map(COUNTY_PALETTE).fillna("#888888")
    markers = np.where(is_ll, "D", "o")  # diamond for LL, circle for non-LL

    for ct, colour in COUNTY_PALETTE.items():
        sub_ll = underserved[is_ll & (underserved["county_type"] == ct)]
        sub_nll = underserved[~is_ll & (underserved["county_type"] == ct)]
        if len(sub_ll):
            axes[0].scatter(
                sub_ll["broadband_rate"], sub_ll["population"],
                c=colour, marker="D", s=40, alpha=0.8, zorder=3,
                label=f"{ct.capitalize()} LL cluster",
            )
        if len(sub_nll):
            axes[0].scatter(
                sub_nll["broadband_rate"], sub_nll["population"],
                c=colour, marker="o", s=18, alpha=0.45, zorder=2,
                label=f"{ct.capitalize()} non-LL",
            )

    axes[0].set_xlabel("Broadband Rate", fontsize=11)
    axes[0].set_ylabel("Tract Population", fontsize=11)
    axes[0].set_title(
        f"Underserved Tracts (broadband < {broadband_threshold:.0%})\n"
        "Diamonds = LL cold-spot clusters; Circles = scattered underserved",
        fontsize=11,
    )
    axes[0].legend(fontsize=8, ncol=2, loc="upper right")

    # Panel 2: household coverage gap
    cbt = coverage_result.get("coverage_by_type", {})
    if cbt:
        groups = [g for g in ["rural", "suburban", "urban"] if g in cbt]
        ll_hh = [cbt[g]["ll_hh"] for g in groups]
        missed_hh = [cbt[g]["underserved_hh"] - cbt[g]["ll_hh"] for g in groups]
        colours_grp = [COUNTY_PALETTE.get(g, "#888") for g in groups]

        x = np.arange(len(groups))
        w = 0.5
        bars_ll = axes[1].bar(x, ll_hh, w, label="Covered by LL targeting",
                               color=colours_grp, alpha=0.9, edgecolor="white")
        bars_miss = axes[1].bar(x, missed_hh, w, bottom=ll_hh,
                                 label="Missed (non-LL underserved)",
                                 color=colours_grp, alpha=0.38, edgecolor="white", hatch="////")

        # Coverage % annotation
        for i, g in enumerate(groups):
            pct = cbt[g]["ll_coverage_pct"]
            total = cbt[g]["underserved_hh"]
            axes[1].text(i, total + total * 0.02, f"{pct:.0f}% covered", ha="center",
                         fontsize=9, fontweight="bold")

        axes[1].set_xticks(x)
        axes[1].set_xticklabels([g.capitalize() for g in groups])
        axes[1].set_ylabel("Underserved Households", fontsize=11)
        axes[1].set_title(
            "Guardrail: LL-Cluster Targeting Coverage by County Type\n"
            "Urban underserved households are largely missed by spatial targeting alone",
            fontsize=11,
        )
        axes[1].legend(fontsize=9)

    missed_pct = coverage_result.get("missed_pct", 0)
    plt.suptitle(
        f"Analytical Tension: Spatial Targeting Misses {missed_pct:.0f}% of Underserved Households",
        fontsize=13, y=1.02,
    )
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_edi_by_cluster(
    gdf: gpd.GeoDataFrame,
    save_path: Path | None = None,
) -> plt.Figure:
    """Box plot of Economic Disadvantage Index by LISA cluster, secondary outcome."""
    if "economic_disadvantage_index" not in gdf.columns or "lisa_cluster" not in gdf.columns:
        raise ValueError("GDF must have economic_disadvantage_index and lisa_cluster columns.")

    cluster_order = ["LL", "LH", "NS", "HL", "HH"]
    cluster_order = [c for c in cluster_order if c in gdf["lisa_cluster"].values]

    fig, ax = plt.subplots(figsize=(9, 5))
    palette = {k: CLUSTER_COLOURS[k] for k in cluster_order}

    plot_data = gdf[gdf["lisa_cluster"].isin(cluster_order)].copy()
    sns.boxplot(
        data=plot_data,
        x="lisa_cluster",
        y="economic_disadvantage_index",
        order=cluster_order,
        palette=palette,
        ax=ax,
        linewidth=1.2,
        fliersize=3,
    )

    ax.set_xlabel("LISA Cluster", fontsize=11)
    ax.set_ylabel("Economic Disadvantage Index (0 = least, 1 = most)", fontsize=11)
    ax.set_title(
        "Secondary Outcome: Economic Disadvantage by LISA Cluster\n"
        "LL cold spots have the highest multi-dimensional deprivation (income + education + broadband)",
        fontsize=12,
    )
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
