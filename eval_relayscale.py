"""Scale-robustness probe for the rotating relay-sink tier.

The 1.50x win was measured at N=100. The review flagged node-count heterogeneity
as a common way papers dodge honest comparison. This checks whether the
rotating relay tier (budgeted 0.5J, rotate_every=50) keeps its margin at
N=200 and N=500 under the SAME per-node energy budget (0.5/1.0J) and identical
20-seed coupled-RNG protocol.

Configs per N: baseline multichain K=1 vs rotating relay (rotate_every=50).
Reports LAST, xBaseline, FND, PDR, PDR>341, relay-dead.
"""
import json
import numpy as np
from clusterchain_h import ClusterChainH
from cch_relaysink import RelayRotationClusterChain

M, A = 0.1, 2.0
MAX_ROUNDS = 6000
SEEDS = [1000 + i * 7 for i in range(20)]


def run(cls, n, seeds, **kw):
    out = []
    for s in seeds:
        import random as _r
        _r.seed(s)
        np.random.seed(s)
        p = cls(n_nodes=n, **kw)
        p.run(MAX_ROUNDS)
        out.append(p)
    return out


def ci(arr):
    arr = np.asarray(arr, float)
    return float(arr.mean()), float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr)))


result = {}
for N in (100, 200, 500):
    base = run(ClusterChainH, N, SEEDS, m=M, a_mult=A, mode='multichain', K=1)
    rot = run(RelayRotationClusterChain, N, SEEDS, m=M, a_mult=A, K=1,
              relay_energy=0.5, rotate_every=50)
    bl = [p.history[-1][0] for p in base]
    rl = [p.history[-1][0] for p in rot]
    pdr = [np.mean([min(1.0, p.history[r][3]) for r in range(min(len(p.history), 2000))])
           for p in rot]
    post = [float(np.mean(getattr(p, 'pdr_after_341', [])))
            if getattr(p, 'pdr_after_341', None) else float('nan') for p in rot]
    dead = [getattr(p, 'relay_dead_round', None) for p in rot]
    result[f'N={N}'] = {
        'BASE_LAST': ci(bl), 'ROT_LAST': ci(rl),
        'xBASE': ci(rl)[0] / ci(bl)[0],
        'ROT_PDR': ci(pdr), 'ROT_PDR_post341': float(np.nanmean(post)),
        'RELAY_DEAD': [d for d in dead if d is not None],
    }

with open('eval_relayscale.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f'{"N":>5s} {"base LAST":>10s} {"rot LAST":>10s} {"xBASE":>6s} '
      f'{"PDR":>5s} {"PDR>341":>7s} {"relayDead":>9s}')
for N in (100, 200, 500):
    r = result[f'N={N}']
    mbd, cbd = r['BASE_LAST']
    mrl, crl = r['ROT_LAST']
    rd = r['RELAY_DEAD']
    print(f'{N:5d} {mbd:10.0f}±{cbd:3.0f} {mrl:10.0f}±{crl:3.0f} '
          f'{r["xBASE"]:6.2f} {r["ROT_PDR"][0]:5.2f} {r["ROT_PDR_post341"]:7.2f} '
          f'{str(rd[0]) if rd else "-":>9s}')
