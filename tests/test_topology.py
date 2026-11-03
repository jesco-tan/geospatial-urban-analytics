import numpy as np
import pytest
from libpysal.weights import lat2W
from src.geo_urban.fetch import make_synthetic_geodataframe
from src.geo_urban.spatial_stats import build_weights, lisa_clusters

@pytest.mark.parametrize("queen,degrees", [(True,{3:4,5:72,8:324}),(False,{2:4,3:72,4:324})])
def test_grid_against_independent_lattice(queen,degrees):
    from collections import Counter
    gdf = make_synthetic_geodataframe()
    w = build_weights(gdf,queen)
    ref = lat2W(20,20,rook=not queen)
    assert w.n_components == 1 and not w.islands
    assert not w.asymmetry(intrinsic=False)
    assert Counter(w.cardinalities.values()) == degrees
    assert w.id_order == gdf.GEOID.tolist()
    for i,id_ in enumerate(w.id_order):
        assert set(w.neighbors[id_]) == {w.id_order[j] for j in ref.neighbors[i]}


def test_row_alignment_survives_shuffle_and_subsets():
    gdf = make_synthetic_geodataframe().sample(frac=1,random_state=9)
    w = build_weights(gdf)
    assert w.id_order == gdf.GEOID.tolist()
    assert len(w.neighbors["060000000"]) == 3
    sub = gdf[gdf.grid_row < 2]
    assert build_weights(sub).n_components == 1


def test_seed_and_adjustment():
    g = make_synthetic_geodataframe()
    a = lisa_clusters(g,"broadband_rate",build_weights(g),n_permutations=999)
    b = lisa_clusters(g,"broadband_rate",build_weights(g),n_permutations=999)
    np.testing.assert_array_equal(a.lisa_p_sim,b.lisa_p_sim)
    assert (a.lisa_p_adjusted >= a.lisa_p_sim).all()
    assert (a.loc[a.lisa_p_adjusted >= .05,"lisa_cluster"] == "NS").all()
