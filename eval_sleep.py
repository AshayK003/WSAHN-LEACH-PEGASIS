"""Verdict run: rotating sleep subset vs baseline.

H1 identity: awake_frac=1.0 reproduces baseline LAST (within 1%).
H2 lifetime: LAST(f=0.7) > 1.2x baseline LAST, awake-PDR800 >= 0.99.
H3 honesty: energy-per-delivered-report(f=0.7) < baseline EPR.
3 coupled seeds (42,142,242), N=100, K=1, MAXR 4000.
Writes eval_sleep.json. Baseline files untouched.
"""
import json
import random
import time

import numpy as np

from cch_sleep import ClusterChainH_SLP
from clusterchain_h import ClusterChainH

SEEDS = (42, 142, 242)
FRACS = (1.0, 0.85, 0.7, 0.5)
MAXR = 4000
KW = dict(n_nodes=100, m=0.1, a_mult=2.0, mode='multichain', K=1)


def run(make):
    lasts, fnds, pdr8, epr = [], [], [], []
    for s in SEEDS:
        random.seed(s)
        np.random.seed(s)
        h = make().run(MAXR)
        lasts.append(h[-1][0])
        fnds.append(min(r for r, a, *_ in h if a < 100))
        w = min(800, len(h))
        pdr8.append(float(np.mean([min(1.0, h[r][3]) for r in range(w)])))
        epr.append(sum(r[2] for r in h) / max(1, sum(r[6] for r in h)))
    return {'LAST': round(float(np.mean(lasts)), 1),
            'FND': round(float(np.mean(fnds)), 1),
            'PDR800': round(float(np.mean(pdr8)), 4),
            'EPR_uJ': round(float(np.mean(epr)) * 1e6, 1)}


out, t0 = {}, time.time()
out['base'] = run(lambda: ClusterChainH(**KW))
print(f"base: LAST {out['base']['LAST']:.0f} FND {out['base']['FND']:.0f} "
      f"PDR {out['base']['PDR800']:.4f} EPR {out['base']['EPR_uJ']:.1f}uJ",
      flush=True)
for f in FRACS:
    out[f'f{f}'] = run(lambda f=f: ClusterChainH_SLP(awake_frac=f, **KW))
    r = out[f'f{f}']
    print(f"f={f}: LAST {r['LAST']:.0f} (x{r['LAST'] / out['base']['LAST']:.2f})"
          f" FND {r['FND']:.0f} PDR {r['PDR800']:.4f} "
          f"EPR {r['EPR_uJ']:.1f}uJ", flush=True)

b = out['base']
h1 = abs(out['f1.0']['LAST'] - b['LAST']) / b['LAST'] <= 0.01
h2 = (out['f0.7']['LAST'] / b['LAST'] > 1.2
      and out['f0.7']['PDR800'] >= 0.99)
h3 = out['f0.7']['EPR_uJ'] < b['EPR_uJ']
print(f"H1 identity (f=1.0 == base): {'PASS' if h1 else 'FAIL'}")
print(f"H2 lifetime (f=0.7 x{out['f0.7']['LAST'] / b['LAST']:.2f} >1.2x, "
      f"PDR {out['f0.7']['PDR800']:.4f}): {'PASS' if h2 else 'FAIL'}")
print(f"H3 honesty (EPR {out['f0.7']['EPR_uJ']:.1f} < {b['EPR_uJ']:.1f}uJ): "
      f"{'PASS' if h3 else 'FAIL'}")
print('VERDICT:', 'WORKS — adopt behind K1-relay check'
      if (h1 and h2 and h3) else 'DOES NOT WORK as framed — file evidence')
print(f"wall {time.time() - t0:.1f}s")
json.dump(out, open('eval_sleep.json', 'w'), indent=2)
print('saved eval_sleep.json')
