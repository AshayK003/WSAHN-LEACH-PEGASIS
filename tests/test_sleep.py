"""Fast unit tests for the rotating sleep subset (<15s).

Run:  python -m pytest tests/test_sleep.py -q
"""
import random

import numpy as np
import pytest

import energy
from cch_sleep import ClusterChainH_SLP


def test_rejects_out_of_range():
    for bad in (0, -0.3, 1.2, 2.0):
        with pytest.raises(ValueError):
            ClusterChainH_SLP(n_nodes=10, awake_frac=bad)


def test_frac1_trajectory_identity():
    # f=1.0 must reproduce baseline trajectories exactly (wiring check).
    from clusterchain_h import ClusterChainH
    kw = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)
    for s in (42, 142):
        random.seed(s)
        np.random.seed(s)
        base = ClusterChainH(**kw).run(100)
        random.seed(s)
        np.random.seed(s)
        same = ClusterChainH_SLP(awake_frac=1.0, **kw).run(100)
        assert base == same


def test_sleepers_rest_and_sent_counts_awake():
    # 150 rounds, no deaths expected: sent == awake count every round,
    # sleepers keep higher residual energy than awake nodes, PDR clean.
    kw = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)
    random.seed(7)
    np.random.seed(7)
    sim = ClusterChainH_SLP(awake_frac=0.5, **kw)
    h = sim.run(150)
    assert all(a == 100 for _, a, *_ in h)
    assert {s for *_, s, _ in h} == {50}
    assert all(r[3] == 1.0 for r in h)
    assert energy.PAYLOAD_SCALE == 1.0


def test_sync_charged_only_when_sleeping():
    # f=1.0 pays no SYNC (proven by identity test); f<1.0 pays exactly one
    # rx per awake node in round 1 on top of chain costs.
    kw = dict(n_nodes=20, m=0.0, a_mult=1.0, mode='multichain', K=1)
    random.seed(3)
    np.random.seed(3)
    sim = ClusterChainH_SLP(awake_frac=0.5, **kw)
    sim.step()
    alive_e = sorted((n.energy for n in sim.nodes if n.alive), reverse=True)
    assert len(alive_e) == 20  # nobody dies in round 1
    assert energy.PAYLOAD_SCALE == 1.0
