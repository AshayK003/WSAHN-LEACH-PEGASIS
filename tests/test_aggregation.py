"""Fast unit tests for the aggregation harness (<10s).

Run:  python -m pytest tests/test_aggregation.py -q
"""
import random

import numpy as np
import pytest

import energy
from cch_aggregation import agg


def test_restores_scale_after_block_and_on_exception():
    assert energy.PAYLOAD_SCALE == 1.0
    with agg(0.7):
        assert energy.PAYLOAD_SCALE == 0.7
    assert energy.PAYLOAD_SCALE == 1.0
    with pytest.raises(RuntimeError):
        with agg(0.5):
            raise RuntimeError('boom')
    assert energy.PAYLOAD_SCALE == 1.0


def test_rejects_out_of_range():
    for bad in (0, -0.5, 1.5, 2.0):
        with pytest.raises(ValueError):
            with agg(bad):
                pass
    assert energy.PAYLOAD_SCALE == 1.0


def test_charges_scale_linearly():
    d = 50.0
    with agg(1.0):
        full = (energy.tx_energy(d), energy.rx_energy(), energy.da_energy())
    with agg(0.5):
        half = (energy.tx_energy(d), energy.rx_energy(), energy.da_energy())
    assert half == pytest.approx(tuple(0.5 * v for v in full))
    assert energy.PAYLOAD_SCALE == 1.0


def test_alpha1_trajectory_identity():
    # alpha=1.0 must reproduce baseline trajectories exactly (wiring check).
    from clusterchain_h import ClusterChainH
    from pegasis import PEGASIS
    for cls, kw in [(ClusterChainH,
                     dict(m=0.1, a_mult=2.0, mode='multichain', K=1)),
                    (PEGASIS, {})]:
        random.seed(42)
        np.random.seed(42)
        base = cls(n_nodes=100, **kw).run(100)
        random.seed(42)
        np.random.seed(42)
        with agg(1.0):
            same = cls(n_nodes=100, **kw).run(100)
        assert base == same


def test_alpha_cuts_energy_before_first_death():
    # No deaths in 150 rounds -> same alive series, strictly less energy.
    from clusterchain_h import ClusterChainH
    kw = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)
    random.seed(7)
    np.random.seed(7)
    full = ClusterChainH(**kw).run(150)
    random.seed(7)
    np.random.seed(7)
    with agg(0.7):
        fused = ClusterChainH(**kw).run(150)
    assert [a for _, a, *_ in full] == [a for _, a, *_ in fused]
    e_full = sum(e for _, _, e, *_ in full)
    e_fused = sum(e for _, _, e, *_ in fused)
    assert e_fused == pytest.approx(0.7 * e_full)
    assert energy.PAYLOAD_SCALE == 1.0
