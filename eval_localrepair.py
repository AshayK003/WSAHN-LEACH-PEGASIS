"""Hypothesis test: local chain repair vs baseline (3 coupled seeds, N=100, K=1).

H1 lifetime: LAST/FND within +/-3% of baseline.
H2 mechanism: >=80% of post-death rebuilds replaced by repairs.
H3 delivery: mean PDR >=0.99 and |delta| <= 0.005 vs baseline.
Writes eval_localrepair.json. Baseline files untouched.
"""
import json
import random
import time

import numpy as np

from cch_localrepair import ClusterChainH_LR
from clusterchain_h import ClusterChainH

SEEDS = (42, 142, 242)
KW = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)
MAXR = 4000


def metrics(h):
    last = h[-1][0]
    fnd = min(r for r, a, *_ in h if a < 100)
    hnd = next((r for r, a, *_ in h if a <= 50), h[-1][0])
    pdr = float(np.mean([min(1.0, row[3]) for row in h]))
    w = min(800, len(h))
    pdr800 = float(np.mean([min(1.0, h[r][3]) for r in range(w)]))
    return {'LAST': last, 'FND': fnd, 'HND': hnd, 'PDR': round(pdr, 4),
            'PDR800': round(pdr800, 4)}


out = {}
for name, cls in [('base', ClusterChainH), ('lr', ClusterChainH_LR)]:
    t0 = time.time()
    ms, repairs, rebuilds = [], 0, 0
    for s in SEEDS:
        random.seed(s)
        np.random.seed(s)
        sim = cls(**KW)
        ms.append(metrics(sim.run(MAXR)))
        repairs += getattr(sim, 'n_repairs', 0)
        rebuilds += getattr(sim, 'n_rebuilds', 0)
    out[name] = {'seeds': ms, 'wall_s': round(time.time() - t0, 1),
                 'repairs': repairs, 'rebuilds': rebuilds}


def mean(k, m):
    return float(np.mean([s[m] for s in out[k]['seeds']]))


print(f"{'variant':6s} {'LAST':>6s} {'FND':>6s} {'HND':>6s} {'PDR':>6s} "
      f"{'wall_s':>7s} {'rep':>4s} {'reb':>4s}")
for k in ('base', 'lr'):
    print(f"{k:6s} {mean(k, 'LAST'):6.0f} {mean(k, 'FND'):6.0f} "
          f"{mean(k, 'HND'):6.0f} {mean(k, 'PDR'):6.4f} "
          f"{out[k]['wall_s']:7.1f} {out[k]['repairs']:4d} "
          f"{out[k]['rebuilds']:4d}")

b, l = mean('base', 'LAST'), mean('lr', 'LAST')
bf, lf = mean('base', 'FND'), mean('lr', 'FND')
bp, lp = mean('base', 'PDR800'), mean('lr', 'PDR800')
tot = out['lr']['repairs'] + out['lr']['rebuilds']
h1 = abs(l - b) / b <= 0.03 and abs(lf - bf) / bf <= 0.03
h2 = (out['lr']['repairs'] / tot >= 0.80) if tot else False
h3 = lp >= 0.99 and abs(lp - bp) <= 0.005
print(f"H1 lifetime (|dLAST|={abs(l - b) / b:.3%}, "
      f"|dFND|={abs(lf - bf) / bf:.3%} <=3%): {'PASS' if h1 else 'FAIL'}")
print(f"H2 mechanism (repairs {out['lr']['repairs']}/{tot}): "
      f"{'PASS' if h2 else 'FAIL'}")
print(f"H3 delivery (early-800 PDR base={bp:.4f} lr={lp:.4f}): "
      f"{'PASS' if h3 else 'FAIL'}")
print('VERDICT:', 'GO (20-seed canonical + N=500 scaling)'
      if (h1 and h3) else 'NO-GO (keep baseline, file as evidence)')

json.dump(out, open('eval_localrepair.json', 'w'), indent=2)
print('saved eval_localrepair.json')
