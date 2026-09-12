"""Fast unit tests for AODV-style local chain repair (<10s).

Run:  python -m pytest tests/test_localrepair.py -q
"""
import random

from cch_localrepair import ClusterChainH_LR, try_local_repair
from clusterchain_h import CCNodeH, build_refined_chain


def _pool(n, seed=11):
    random.seed(seed)
    return [CCNodeH(i, random.uniform(0, 100), random.uniform(0, 100), 0.5)
            for i in range(n)]


def _sink():
    return CCNodeH(-1, 50, 175, float('inf'))


def _linked_ok(path, dead_id=None):
    ids = {n.id for n in path}
    assert dead_id not in ids
    assert path[-1].is_terminus is True
    assert path[-1].chain_next is None
    for n in path[:-1]:
        assert n.chain_next in ids
        assert n.is_terminus is False


def _order(n=8, seed=11):
    pool = _pool(n, seed)
    return pool, build_refined_chain(pool, _sink(), rotate=True, refine=True)


def test_repair_single_middle_death():
    pool, order = _order()
    victim = order[3]
    alive = {n.id for n in pool if n.id != victim.id}
    patched = try_local_repair(list(order), alive, _sink(), rotate=True)
    assert patched is not None
    assert len(patched) == 7
    _linked_ok(patched, dead_id=victim.id)


def test_repair_terminus_death_refarms_terminus():
    pool, order = _order()
    victim = order[-1]
    alive = {n.id for n in pool if n.id != victim.id}
    patched = try_local_repair(list(order), alive, _sink(), rotate=True)
    assert patched is not None
    assert len(patched) == 7
    _linked_ok(patched, dead_id=victim.id)


def test_repair_head_death():
    pool, order = _order()
    victim = order[0]
    alive = {n.id for n in pool if n.id != victim.id}
    patched = try_local_repair(list(order), alive, _sink(), rotate=True)
    assert patched is not None
    assert len(patched) == 7
    _linked_ok(patched, dead_id=victim.id)


def test_repair_two_deaths_returns_none():
    pool, order = _order()
    dead = {order[2].id, order[5].id}
    alive = {n.id for n in pool if n.id not in dead}
    assert try_local_repair(list(order), alive, _sink()) is None


def test_repair_no_death_returns_none():
    pool, order = _order()
    alive = {n.id for n in pool}
    assert try_local_repair(list(order), alive, _sink()) is None


def test_lr_matches_baseline_before_first_death():
    # No deaths in 100 rounds -> repair path never engages -> trajectories
    # must be bit-identical to baseline (wiring check).
    import numpy as np
    from clusterchain_h import ClusterChainH
    kw = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)
    for s in (42, 142):
        random.seed(s)
        np.random.seed(s)
        base = ClusterChainH(**kw).run(100)
        random.seed(s)
        np.random.seed(s)
        lr = ClusterChainH_LR(**kw).run(100)
        assert [a for _, a, *_ in base] == [a for _, a, *_ in lr]
        assert [e for _, _, e, *_ in base] == [e for _, _, e, *_ in lr]
        assert all(a == 100 for _, a, *_ in lr)
