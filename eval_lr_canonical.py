"""Canonical + scaling verdict: local repair vs baseline.

Phase 1: 20 coupled seeds (canonical [1000+i*7]), N=100, K=1, MAXR 4000.
Phase 2: 3 coupled seeds (42,142,242), N=500, K=1, MAXR 6000.
Reports mean +/-95% CI for LAST/FND, early-800 PDR, wall time, rep/reb.
Writes eval_lr_canonical.json. Baseline files untouched.
"""
import json
import random
import time

import numpy as np

from cch_localrepair import ClusterChainH_LR
from clusterchain_h import ClusterChainH


def ci(arr):
    a = np.asarray(arr, float)
    return float(a.mean()), float(1.96 * a.std(ddof=1) / np.sqrt(len(a)))


def run_variant(cls, n, seeds, maxr, kw_extra):
    kw = dict(n_nodes=n, m=0.1, a_mult=2.0, mode='multichain', K=1)
    kw.update(kw_extra)
    lasts, fnds, pdr8, rep, reb, t0 = [], [], [], 0, 0, time.time()
    for s in seeds:
        random.seed(s)
        np.random.seed(s)
        sim = cls(**kw)
        h = sim.run(maxr)
        lasts.append(h[-1][0])
        fnds.append(min(r for r, a, *_ in h if a < n))
        w = min(800, len(h))
        pdr8.append(float(np.mean([min(1.0, h[r][3]) for r in range(w)])))
        rep += getattr(sim, 'n_repairs', 0)
        reb += getattr(sim, 'n_rebuilds', 0)
    return {'LAST': ci(lasts), 'FND': ci(fnds), 'PDR800': ci(pdr8),
            'wall_s': round(time.time() - t0, 1),
            'repairs': rep, 'rebuilds': reb}


out = {}
seeds20 = [1000 + i * 7 for i in range(20)]
for name, cls in [('base', ClusterChainH), ('lr', ClusterChainH_LR)]:
    out[f'N100_{name}'] = run_variant(cls, 100, seeds20, 4000, {})
    print(f"N100_{name}: LAST {out[f'N100_{name}']['LAST'][0]:.0f}"
          f" +/-{out[f'N100_{name}']['LAST'][1]:.0f} | FND "
          f"{out[f'N100_{name}']['FND'][0]:.0f} | PDR800 "
          f"{out[f'N100_{name}']['PDR800'][0]:.4f} | "
          f"wall {out[f'N100_{name}']['wall_s']}s | rep "
          f"{out[f'N100_{name}']['repairs']}/"
          f"{out[f'N100_{name}']['repairs'] + out[f'N100_{name}']['rebuilds']}",
          flush=True)

for name, cls in [('base', ClusterChainH), ('lr', ClusterChainH_LR)]:
    out[f'N500_{name}'] = run_variant(cls, 500, (42, 142, 242), 6000, {})
    print(f"N500_{name}: LAST {out[f'N500_{name}']['LAST'][0]:.0f}"
          f" +/-{out[f'N500_{name}']['LAST'][1]:.0f} | FND "
          f"{out[f'N500_{name}']['FND'][0]:.0f} | PDR800 "
          f"{out[f'N500_{name}']['PDR800'][0]:.4f} | "
          f"wall {out[f'N500_{name}']['wall_s']}s | rep "
          f"{out[f'N500_{name}']['repairs']}/"
          f"{out[f'N500_{name}']['repairs'] + out[f'N500_{name}']['rebuilds']}",
          flush=True)

b, l = out['N100_base']['LAST'][0], out['N100_lr']['LAST'][0]
print(f"N100 dLAST={(l - b) / b:+.2%}, "
      f"dFND={(out['N100_lr']['FND'][0] - out['N100_base']['FND'][0]) / out['N100_base']['FND'][0]:+.2%}")
b5, l5 = out['N500_base']['LAST'][0], out['N500_lr']['LAST'][0]
print(f"N500 dLAST={(l5 - b5) / b5:+.2%}, "
      f"dFND={(out['N500_lr']['FND'][0] - out['N500_base']['FND'][0]) / out['N500_base']['FND'][0]:+.2%}, "
      f"wall {out['N500_base']['wall_s']}s -> {out['N500_lr']['wall_s']}s")

json.dump(out, open('eval_lr_canonical.json', 'w'), indent=2)
print('saved eval_lr_canonical.json')
