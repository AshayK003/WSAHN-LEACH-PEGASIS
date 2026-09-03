"""Fast unit tests (<5s): energy model, chain builders, election math, guards.

Run:  python -m pytest tests/test_fast.py -q
Full: python -m pytest tests -q  (includes slow 60s+ simulation regressions)
"""
import math
import random

import numpy as np
import pytest

from energy import (
    D0, E_FS, E_MP, PACKET_SIZE,
    da_energy, in_range, rx_energy, tx_energy,
)
import energy


def test_tx_energy_free_space_vs_multipath():
    # Below D0: quadratic; above: quartic. Continuity at D0 is approximate
    # by construction of the crossover.
    e_short = tx_energy(10.0)
    e_long = tx_energy(150.0)
    assert e_long > e_short > 0
    # Free-space branch check against closed form
    assert tx_energy(10.0) == pytest.approx(
        PACKET_SIZE * (50e-9 + E_FS * 100.0))
    assert tx_energy(150.0) == pytest.approx(
        PACKET_SIZE * (50e-9 + E_MP * 150.0 ** 4))


def test_d0_value():
    assert D0 == pytest.approx((E_FS / E_MP) ** 0.5)
    assert D0 == pytest.approx(87.7, abs=0.5)


def test_rx_da_positive():
    assert rx_energy() > 0
    assert da_energy() > 0


def test_in_range_default_unlimited():
    assert energy.COMM_RANGE is None
    assert in_range(1e6) is True


def test_partition_into_chains_covers_all_nodes():
    from clusterchain_h import CCNodeH, partition_into_chains
    random.seed(0)
    alive = [CCNodeH(i, random.uniform(0, 100), random.uniform(0, 100), 0.5)
             for i in range(10)]
    chains = partition_into_chains(alive, 3)
    assert sum(len(c) for c in chains) == 10
    assert partition_into_chains(alive, 1) == [alive]


def test_build_refined_chain_terminus_last_and_linked():
    from clusterchain_h import CCNodeH, build_refined_chain
    random.seed(1)
    pool = [CCNodeH(i, random.uniform(0, 100), random.uniform(0, 100), 0.5)
            for i in range(8)]
    sink = CCNodeH(-1, 50, 175, float('inf'))
    path = build_refined_chain(pool, sink, rotate=True, refine=True)
    assert len(path) == 8
    assert path[-1].is_terminus is True
    ids = {n.id for n in path}
    for n in path[:-1]:
        assert n.chain_next in ids
    assert path[-1].chain_next is None


def test_mst_chain_covers_pool():
    from clusterchain_h import CCNodeH, mst_chain
    random.seed(2)
    pool = [CCNodeH(i, random.uniform(0, 100), random.uniform(0, 100), 0.5)
            for i in range(6)]
    out = mst_chain(pool)
    assert {n.id for n in out} == {n.id for n in pool}


def test_optimal_k_small_and_bounded():
    from clusterchain_h import optimal_k
    assert optimal_k(100, 1) == 4
    assert optimal_k(50, 1) == 3
    assert optimal_k(2) == 1


def test_sep_standard_probabilities():
    # Standard SEP: p_n = p/(1+a*m), p_a = p*(1+a)/(1+a*m), a = a_mult-1.
    from sep import SEP
    random.seed(0)
    np.random.seed(0)
    s = SEP(n_nodes=100, m=0.1, a_mult=2.0, p_opt=0.1)
    a = 1.0
    assert s.p / (1 + a * 0.1) == pytest.approx(0.1 / 1.1)
    # Expected CH count per round ~ p_opt * N
    counts = []
    for _ in range(30):
        s._select_cluster_heads()
        counts.append(sum(1 for n in s.nodes if n.is_ch))
    assert 5 < float(np.mean(counts)) < 16


def test_leach_validates_inputs():
    from leach import LEACH
    with pytest.raises(ValueError):
        LEACH(n_nodes=100, p_ch=0.0)
    with pytest.raises(ValueError):
        LEACH(n_nodes=100, p_ch=1.5)
    with pytest.raises(ValueError):
        LEACH(n_nodes=0)


def test_node_consume_marks_dead():
    from leach import Node
    n = Node(0, 0.0, 0.0, energy=1e-9)
    assert n.consume(1e-6) is True
    assert n.alive is False
    assert n.energy == 0
