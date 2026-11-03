"""Reproduce the topology-corrected synthetic run. Run from repository root."""
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.geo_urban.fetch import make_synthetic_geodataframe
from src.geo_urban.spatial_stats import build_weights, global_morans_i, lisa_clusters, subgroup_morans_i
from src.geo_urban.regression import (run_ols,run_spatial_lag,run_spatial_error,compare_models,run_subgroup_ols,population_coverage_analysis)
from src.geo_urban import visualise as viz
from src.geo_urban.maps import lisa_map,choropleth_map,county_type_map

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"
SEED=42
PERMUTATIONS=9999
COV=["log_income","bach_rate","log_population"]

def main():
    g=make_synthetic_geodataframe(seed=SEED)
    results={}
    frames={}
    for name,queen in [("queen",True),("rook",False)]:
        w=build_weights(g,queen)
        assert w.n_components==1 and not w.islands and not w.asymmetry(intrinsic=False)
        assert w.id_order==g.GEOID.tolist()
        local=lisa_clusters(g,"broadband_rate",w,n_permutations=PERMUTATIONS,seed=SEED)
        raw=local.copy();raw["lisa_cluster"]=raw.lisa_cluster_raw
        frames[name]=local
        results[name]={"topology":{"components":w.n_components,"islands":w.islands,"mean_degree":w.mean_neighbors,"id_order":w.id_order},
          "global_moran":global_morans_i(g,"broadband_rate",w,PERMUTATIONS,SEED),
          "lisa_cluster_counts":local.lisa_cluster.value_counts().to_dict(),
          "raw_cluster_counts":local.lisa_cluster_raw.value_counts().to_dict(),
          "guardrail":population_coverage_analysis(local),"raw_guardrail":population_coverage_analysis(raw),
          "spatial_lag":run_spatial_lag(g,"broadband_rate",COV,w),"spatial_error":run_spatial_error(g,"broadband_rate",COV,w)}
    primary=results["queen"];g=frames["queen"];w=build_weights(g)
    ols=run_ols(g,"broadband_rate",COV)
    summary={"scenario":"Synthetic broadband targeting, verified grid v2","n_tracts":len(g),"data_source":"synthetic (structured latent model)",
      "broadband_threshold":.65,"seed":SEED,"permutations":PERMUTATIONS,"correction":"Benjamini-Yekutieli across all 400 two-sided local pseudo p-values",
      "primary_adjacency":"queen",**primary,"sensitivity":results,"ols_full":ols,
      "subgroup_moran":subgroup_morans_i(g,"broadband_rate",n_permutations=PERMUTATIONS).to_dict("records")}
    OUT.mkdir(exist_ok=True)
    def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n",encoding="utf-8", newline="\n")
    save("run_summary.json",summary)
    (OUT/"cells.geojson").write_text(g.to_json(),encoding="utf-8", newline="\n")
    compare=compare_models([ols,primary["spatial_lag"],primary["spatial_error"]])
    compare.to_csv(OUT/"regression_comparison.csv",index=False, lineterminator="\n")
    subgroup=run_subgroup_ols(g,"broadband_rate",COV)
    for name,fig in [
      ("lisa_cluster_map.png",viz.plot_lisa_static(g)),
      ("moran_scatter.png",viz.plot_moran_scatter(g,"broadband_rate",w,primary["global_moran"]["moran_i"],primary["global_moran"]["p_value_sim"])),
      ("guardrail_analysis.png",viz.plot_guardrail(g,primary["guardrail"])),
      ("regression_comparison.png",viz.plot_regression_comparison(compare)),
      ("broadband_distribution.png",viz.plot_broadband_distribution(g)),
      ("subgroup_regression.png",viz.plot_subgroup_regression(subgroup)),
      ("edi_by_cluster.png",viz.plot_edi_by_cluster(g))]:
        fig.savefig(OUT/name,dpi=150,bbox_inches="tight");plt.close(fig)
    lisa_map(g,OUT/"choropleth_lisa.html")
    county_type_map(g,OUT/"choropleth_county_type.html")
    for col,name in [("broadband_rate","broadband"),("median_household_income","income")]:
        choropleth_map(g,col,save_path=OUT/f"choropleth_{name}.html")
    for html in OUT.glob("choropleth_*.html"):
        html.write_text("\n".join(line.rstrip() for line in html.read_text(encoding="utf-8").splitlines())+"\n",encoding="utf-8", newline="\n")
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs={p.relative_to(ROOT).as_posix():digest(p) for p in sorted((ROOT/"src").rglob("*.py"))}
    inputs["scripts/run_analysis.py"]=digest(Path(__file__))
    manifest={"status":"complete","starting_commit":subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip(),
      "python":platform.python_version(),"parameters":{"seed":SEED,"permutations":PERMUTATIONS,"primary":"queen","sensitivity":"rook","alpha":.05,"correction":"fdr_by","tails":"two-sided: min(1,2*esda.p_sim)"},
      "inputs":inputs,"packages":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()},
      "outputs":{p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in ("manifest.json","report.html","broadband-equity-landscape.webp","reproduction.log")},
      "tolerance":"Counts and classifications exact; floating model coefficients absolute tolerance 1e-6 on pinned environment; HTML generated IDs need not be byte-identical."}
    save("manifest.json",manifest)
    print(json.dumps({k:{"moran":v["global_moran"],"clusters":v["lisa_cluster_counts"],"coverage":v["guardrail"]} for k,v in results.items()},indent=2))

if __name__=="__main__":main()
