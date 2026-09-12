"""Robustness curve: CCH-K1 vs PEGASIS margin under fusion traffic.

H1 identity: alpha=1.0 reproduces the published baselines.
H2 robustness: CCH-K1/PEGASIS LAST margin stays >1.2x for alpha in
    {1.0, 0.9, 0.7}.
3 coupled seeds (42,142,242), N=100, MAXR 4000. Writes eval_aggregation.json.
"""
import json
import random
import time

import numpy as np

from cch_aggregation import agg
from clusterchain_h import ClusterChainH
from pegasis import PEGASIS

SEEDS = (42, 142, 242)
ALPHAS = (1.0, 0.9, 0.7)
MAXR = 4000


def run(cls, alpha, **kw):
    lasts, fnds, pdr8 = [], [], []
    for s in SEEDS:
        random.seed(s)
        np.random.seed(s)
        with agg(alpha):
            h = cls(n_nodes=100, **kw).run(MAXR)
        lasts.append(h[-1][0])
        fnds.append(min(r for r, a, *_ in h if a < 100))
        w = min(800, len(h))
        pdr8.append(float(np.mean([min(1.0, h[r][3]) for r in range(w)])))
    return {'LAST': round(float(np.mean(lasts)), 1),
            'FND': round(float(np.mean(fnds)), 1),
            'PDR800': round(float(np.mean(pdr8)), 4)}


out, t0 = {}, time.time()
for a in ALPHAS:
    out[f'PEGASIS_a{a}'] = run(PEGASIS, a, m=0.1, a_mult=2.0)
    out[f'CCHK1_a{a}'] = run(ClusterChainH, a, m=0.1, a_mult=2.0,
                             mode='multichain', K=1)
    pg, cch = out[f'PEGASIS_a{a}']['LAST'], out[f'CCHK1_a{a}']['LAST']
    print(f"alpha={a}: PEGASIS {pg:.0f} | CCH-K1 {cch:.0f} | "
          f"margin x{cch / pg:.2f} | PDR "
          f"{out[f'PEGASIS_a{a}']['PDR800']:.4f}/"
          f"{out[f'CCHK1_a{a}']['PDR800']:.4f}", flush=True)

m1 = out['CCHK1_a1.0']['LAST'] / out['PEGASIS_a1.0']['LAST']
margins = [out[f"CCHK1_a{a}"]['LAST'] / out[f'PEGASIS_a{a}']['LAST']
           for a in ALPHAS]
h1 = (abs(out['CCHK1_a1.0']['LAST'] - 3038) / 3038 <= 0.10
      and abs(out['PEGASIS_a1.0']['LAST'] - 2291) / 2291 <= 0.10)
h2 = all(m > 1.2 for m in margins)
print(f"H1 identity (a=1.0 near published 3038/2291): "
      f"{'PASS' if h1 else 'FAIL'}")
print(f"H2 robustness (margins {[f'{m:.2f}' for m in margins]} >1.2x): "
      f"{'PASS' if h2 else 'FAIL'}")
print(f"wall {time.time() - t0:.1f}s")
json.dump(out, open('eval_aggregation.json', 'w'), indent=2)
print('saved eval_aggregation.json')
