"""Regression / sanity tests for ClusterChain-H and baselines.

Run:  internals\\.venv\\Scripts\\python.exe -m pytest tests -q
"""
import random
import numpy as np
import pytest
from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH
from hpegasis import HPEGASIS

pytestmark = pytest.mark.slow  # full-simulation regressions (60s+); fast unit tests live in test_fast.py


def _last(hists):
    return [h[-1][0] for h in hists if h]


def _early_pdr(hists, w=800):
    return [float(np.mean([min(1.0, h[r][3]) for r in range(min(w, len(h)))]))
            for h in hists if h]


def _run(cls, n_nodes=100, seeds=(42, 142, 242), **kw):
    out = []
    for s in seeds:
        random.seed(s)
        np.random.seed(s)
        out.append(cls(n_nodes=n_nodes, **kw).run(3000))
    return out


def test_all_protocols_run_and_alive_nonincreasing():
    for cls, kw in [(LEACH, {}), (PEGASIS, {}), (SEP, dict(m=0.1, a_mult=2.0)),
                    (DEEC, dict(m=0.1, a_mult=2.0)),
                    (ClusterChainH, dict(m=0.1, a_mult=2.0, mode='multichain', K=3)),
    (HPEGASIS, dict(m=0.1, a_mult=2.0))]:
        h = _run(cls, **kw)[0]
        alive = [a for _, a, *_ in h]
        assert all(alive[i] >= alive[i + 1] for i in range(len(alive) - 1)), \
            f"{cls.__name__} alive count increased"
        assert alive[-1] >= 0


def test_identity_bug_fixed_clustered_pdr_high():
    # The node-identity bug made member data discarded -> PDR ~0.04. Ensure fixed.
    h = _run(ClusterChainH, m=0.1, a_mult=2.0, mode='clustered', K=10)
    pdr = np.mean(_early_pdr(h))
    assert pdr > 0.9, f"clustered PDR too low: {pdr}"


def test_multichain_pdr_one():
    h = _run(ClusterChainH, m=0.1, a_mult=2.0, mode='multichain', K=3)
    pdr = np.mean(_early_pdr(h))
    assert pdr > 0.95, f"multichain PDR too low: {pdr}"


def test_cch_beats_pegasis_lifetime_homogeneous():
    # Geometry + rotating near-sink terminus should beat vanilla PEGASIS even
    # without heterogeneity.
    pg = _last(_run(PEGASIS))
    cch = _last(_run(ClusterChainH, m=0.0, a_mult=1.0, mode='multichain', K=1))
    assert np.mean(cch) > np.mean(pg) * 1.2, \
        f"CCH({np.mean(cch):.0f}) not >1.2x PEGASIS({np.mean(pg):.0f})"


def test_cch_beats_pegasis_leach_heterogeneous():
    leach = np.mean(_last(_run(LEACH)))
    peg = np.mean(_last(_run(PEGASIS)))
    cch = np.mean(_last(_run(ClusterChainH, m=0.1, a_mult=2.0, mode='multichain', K=3)))
    assert cch > peg * 1.5, f"CCH({cch:.0f}) not >1.5x PEGASIS({peg:.0f})"
    assert cch > leach * 2.0, f"CCH({cch:.0f}) not >2x LEACH({leach:.0f})"


def test_heterogeneity_improves_cch():
    homo = np.mean(_last(_run(ClusterChainH, m=0.0, a_mult=1.0, mode='multichain', K=3)))
    het = np.mean(_last(_run(ClusterChainH, m=0.1, a_mult=2.0, mode='multichain', K=3)))
    assert het > homo, f"heterogeneity did not help ({het:.0f} <= {homo:.0f})"


def test_relay_mode_beats_pegasis_homogeneous():
    # First-class relay mode (rotating relay-sink tier) should beat vanilla
    # PEGASIS by ~2x in the homogeneous setting, with PDR intact.
    pg = _last(_run(PEGASIS, n_nodes=100))
    relay = _run(ClusterChainH, n_nodes=100, m=0.0, a_mult=1.0,
                 mode='relay', K=1)
    relay_last = np.mean([h[-1][0] for h in relay])
    relay_pdr = np.mean([np.mean([min(1.0, r[3]) for r in h[:800]]) for h in relay])
    assert relay_last > np.mean(pg) * 1.8, \
        f"relay({relay_last:.0f}) not >1.8x PEGASIS({np.mean(pg):.0f})"
    assert relay_pdr > 0.9, f"relay PDR too low: {relay_pdr}"
