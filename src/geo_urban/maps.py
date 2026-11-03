"""Folium choropleth builders and static map helpers."""

from __future__ import annotations

import json
import numpy as np
import geopandas as gpd
import folium
from pathlib import Path


CLUSTER_COLOURS = {
    "HH": "#d7191c",
    "LL": "#2c7bb6",
    "HL": "#fdae61",
    "LH": "#abd9e9",
    "NS": "#eeeeee",
}

COUNTY_TYPE_COLOURS = {
    "urban": "#5e3c99",
    "suburban": "#b2abd2",
    "rural": "#fdb863",
}


def choropleth_map(
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str = "",
    caption: str = "",
    colormap: str = "YlOrRd",
    save_path: Path | None = None,
) -> folium.Map:
    """Build a Folium choropleth for a single numeric column."""
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    centre = [gdf_wgs84.geometry.centroid.y.mean(), gdf_wgs84.geometry.centroid.x.mean()]

    m = folium.Map(location=centre, zoom_start=7, tiles="CartoDB positron")

    tooltip_cols = ["GEOID", column]
    extra_candidates = [
        "median_household_income", "broadband_rate", "bach_rate",
        "county_type", "economic_disadvantage_index",
    ]
    extra = [c for c in extra_candidates if c in gdf_wgs84.columns and c != column]
    tooltip_cols += extra[:3]

    # Include all tooltip columns in the GeoJSON so Folium can access them
    geojson_cols = list(dict.fromkeys(["GEOID", "geometry"] + tooltip_cols))
    geojson_cols = [c for c in geojson_cols if c in gdf_wgs84.columns]
    geojson_str = gdf_wgs84[geojson_cols].to_json()

    folium.Choropleth(
        geo_data=geojson_str,
        data=gdf_wgs84[["GEOID", column]],
        columns=["GEOID", column],
        key_on="feature.properties.GEOID",
        fill_color=colormap,
        fill_opacity=0.7,
        line_opacity=0.1,
        legend_name=caption or column,
        nan_fill_color="white",
    ).add_to(m)

    folium.GeoJson(
        geojson_str,
        style_function=lambda f: {"fillOpacity": 0, "weight": 0},
        tooltip=folium.GeoJsonTooltip(fields=tooltip_cols, aliases=tooltip_cols),
    ).add_to(m)

    if title:
        title_html = (
            f'<h4 style="position:fixed;top:10px;left:60px;z-index:1000;'
            f'background:white;padding:5px;border-radius:4px">{title}</h4>'
        )
        m.get_root().html.add_child(folium.Element(title_html))

    if save_path:
        m.save(str(save_path))
    return m


def lisa_map(
    gdf: gpd.GeoDataFrame,
    save_path: Path | None = None,
) -> folium.Map:
    """Colour tracts by LISA cluster type (HH/LL/HL/LH/NS)."""
    gdf_wgs84 = gdf.to_crs(epsg=4326).copy()
    centre = [gdf_wgs84.geometry.centroid.y.mean(), gdf_wgs84.geometry.centroid.x.mean()]

    m = folium.Map(location=centre, zoom_start=7, tiles="CartoDB positron")
    geojson_data = json.loads(gdf_wgs84.to_json())

    def style_fn(feature):
        cluster = feature["properties"].get("lisa_cluster", "NS")
        return {
            "fillColor": CLUSTER_COLOURS.get(cluster, "#eeeeee"),
            "color": "white",
            "weight": 0.3,
            "fillOpacity": 0.78,
        }

    tooltip_fields = ["GEOID", "lisa_cluster", "broadband_rate", "population"]
    if "county_type" in gdf_wgs84.columns:
        tooltip_fields.append("county_type")
    if "economic_disadvantage_index" in gdf_wgs84.columns:
        tooltip_fields.append("economic_disadvantage_index")

    folium.GeoJson(
        geojson_data,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=["Tract", "LISA Cluster", "Broadband Rate", "Population"]
            + (["County Type"] if "county_type" in gdf_wgs84.columns else [])
            + (["EDI"] if "economic_disadvantage_index" in gdf_wgs84.columns else []),
        ),
    ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
                padding:12px;border:1px solid #aaa;font-size:12px;border-radius:4px">
      <b>LISA Clusters, Broadband Rate</b><br>
      <span style="background:#d7191c;padding:2px 10px">&nbsp;</span> HH &ndash; Hot spot (high broadband cluster)<br>
      <span style="background:#2c7bb6;padding:2px 10px">&nbsp;</span> LL &ndash; Relative low-low pattern, not eligibility<br>
      <span style="background:#fdae61;padding:2px 10px">&nbsp;</span> HL &ndash; Outlier (high tract, low neighbours)<br>
      <span style="background:#abd9e9;padding:2px 10px">&nbsp;</span> LH &ndash; Outlier (low tract, high neighbours)<br>
      <span style="background:#eeeeee;padding:2px 10px">&nbsp;</span> NS &ndash; Not significant
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    if save_path:
        m.save(str(save_path))
    return m


def county_type_map(
    gdf: gpd.GeoDataFrame,
    save_path: Path | None = None,
) -> folium.Map:
    """Colour tracts by county_type (urban / suburban / rural)."""
    gdf_wgs84 = gdf.to_crs(epsg=4326).copy()
    centre = [gdf_wgs84.geometry.centroid.y.mean(), gdf_wgs84.geometry.centroid.x.mean()]

    m = folium.Map(location=centre, zoom_start=7, tiles="CartoDB positron")
    geojson_data = json.loads(gdf_wgs84.to_json())

    def style_fn(feature):
        ct = feature["properties"].get("county_type", "suburban")
        return {
            "fillColor": COUNTY_TYPE_COLOURS.get(ct, "#cccccc"),
            "color": "white",
            "weight": 0.3,
            "fillOpacity": 0.72,
        }

    tooltip_fields = ["GEOID", "county_type", "broadband_rate", "median_household_income"]
    if "economic_disadvantage_index" in gdf_wgs84.columns:
        tooltip_fields.append("economic_disadvantage_index")

    folium.GeoJson(
        geojson_data,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=["Tract", "County Type", "Broadband Rate", "Median Income", "EDI"],
        ),
    ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
                padding:12px;border:1px solid #aaa;font-size:12px;border-radius:4px">
      <b>County Type</b><br>
      <span style="background:#5e3c99;padding:2px 10px">&nbsp;</span> Urban (income-driven broadband gap)<br>
      <span style="background:#b2abd2;padding:2px 10px">&nbsp;</span> Synthetic suburban (generated drivers)<br>
      <span style="background:#fdb863;padding:2px 10px">&nbsp;</span> Synthetic rural category
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    if save_path:
        m.save(str(save_path))
    return m
