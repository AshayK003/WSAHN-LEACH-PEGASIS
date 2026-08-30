"""Consistency probe: PEGASIS + CCH-K1 + rotating relay in ONE coupled-seed
run, so the README's new rotating-relay row has a vs-PEGASIS ratio that shares
the exact same topology set as the baseline and PEGASIS numbers.

All three use the SAME 20 seeds, both RNGs seeded, identical deployment.
"""
import json
import numpy as np
from pegasis import PEGASIS
from clusterchain_h import ClusterChainH
from cch_relaysink import RelayRotationClusterChain

M, A = 0.1, 2.0
MAX_ROUNDS = 6000
SEEDS = [1000 + i * 7 for i in range(20)]


def run(cls, **kw):
    out = []
    for s in SEEDS:
        import random as _r
        _r.seed(s)
        np.random.seed(s)
        p = cls(n_nodes=100, m=M, a_mult=A, **kw)
        p.run(MAX_ROUNDS)
        out.append(p.history[-1][0])
    return out


def ci(a):
    a = np.asarray(a, float)
    return float(a.mean()), float(1.96 * a.std(ddof=1) / np.sqrt(len(a)))


peg = run(PEGASIS)
base = run(ClusterChainH, mode='multichain', K=1)
rot = run(RelayRotationClusterChain, K=1, relay_energy=0.5, rotate_every=50)

pm, pc = ci(peg)
bm, bc = ci(base)
rm, rc = ci(rot)
res = {
    'PEGASIS': [pm, pc],
    'CCH-K1': [bm, bc],
    'RotatingRelay': [rm, rc],
    'rot_vs_peg': rm / pm,
    'rot_vs_base': rm / bm,
    'base_vs_peg': bm / pm,
}
with open('eval_consistency.json', 'w') as f:
    json.dump(res, f, indent=2)
print(f'PEGASIS       {pm:7.0f}±{pc:3.0f}')
print(f'CCH-K1        {bm:7.0f}±{bc:3.0f}  ({bm/pm:.2f}x PEG)')
print(f'RotatingRelay {rm:7.0f}±{rc:3.0f}  ({rm/pm:.2f}x PEG, {rm/bm:.2f}x base)')
