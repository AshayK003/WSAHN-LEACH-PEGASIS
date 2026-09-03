"""Supplementary evidence for REPORT Sections 9.2/9.3/9.4 + README relay row.

Fills the three tables that previously had no checked-in JSON evidence:
  1. Per-class fairness + E x D (9.2): first-normal-death / first-advanced-death
     from the core protocol's class_history, plus E x D over the stable window.
  2. Homogeneous ablation (9.3): PEGASIS vs CCH-K1 vs first-class relay-K1,
     all homogeneous (m=0.0), 20 coupled seeds.
  3. N=200 heterogeneous scale table (9.4): LEACH/PEGASIS/SEP/DEEC/CCH-K3.
  4. First-class relay-K1 (heterogeneous, 20 seeds): LAST/PDR/DELAY behind the
     README relay row (cross-checks the legacy RelayRotationClusterChain
     harness used in eval_consistency.py).

All runs use coupled seeding (random + numpy). Saves eval_supplement.json.
"""
import json
import random
import numpy as np

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH

M, A = 0.1, 2.0
MAXR = 6000
SEEDS20 = [1000 + i * 7 for i in range(20)]
SEEDS200 = [2000 + i * 11 for i in range(8)]


def run(cls, n, seeds, **kw):
    protos = []
    for s in seeds:
        random.seed(s)
        np.random.seed(s)
        p = cls(n_nodes=n, **kw)
        p.run(MAXR)
        protos.append(p)
    return protos


def ci(arr):
    arr = np.asarray(arr, float)
    return [float(arr.mean()), float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr)))]


def window_stats(protos, w=1500):
    pdr = [float(np.mean([min(1.0, h[r][3]) for r in range(min(w, len(h)))]))
           for h in (p.history for p in protos)]
    dly = [float(np.mean([h[r][4] for r in range(min(w, len(h)))]))
           for h in (p.history for p in protos)]
    nrg = [float(np.mean([h[r][2] for r in range(min(w, len(h)))]))
           for h in (p.history for p in protos)]
    last = [p.history[-1][0] for p in protos]
    return {
        'LAST': ci(last),
        'PDR': ci(pdr),
        'DELAY': ci(dly),
        'E_x_D': ci(np.asarray(nrg) * np.asarray(dly)),
    }


def per_class(protos, m, n):
    """First-death round per node class from class_history."""
    n_adv0 = int(round(m * n))
    n_norm0 = n - n_adv0
    fn_norm, fn_adv = [], []
    for p in protos:
        rn = next((r for r, a, nn in p.class_history if nn < n_norm0), None)
        ra = next((r for r, a, _ in p.class_history if a < n_adv0), None)
        if rn is not None:
            fn_norm.append(rn)
        if ra is not None:
            fn_adv.append(ra)
    return {'first_normal': ci(fn_norm), 'first_adv': ci(fn_adv)}


res = {}

# ---- 1. per-class fairness + ExD, heterogeneous N=100 ----
for K in (1, 2, 3):
    ps = run(ClusterChainH, 100, SEEDS20, m=M, a_mult=A, mode='multichain', K=K)
    res[f'perclass-K{K}'] = {**window_stats(ps), **per_class(ps, M, 100)}

# ---- 2. homogeneous ablation, N=100 ----
res['homo-PEGASIS'] = window_stats(run(PEGASIS, 100, SEEDS20))
res['homo-CCH-K1'] = window_stats(
    run(ClusterChainH, 100, SEEDS20, m=0.0, a_mult=1.0, mode='multichain', K=1))
res['homo-relay-K1'] = window_stats(
    run(ClusterChainH, 100, SEEDS20, m=0.0, a_mult=1.0, mode='relay', K=1))

# ---- 3. N=200 heterogeneous scale table ----
ps200 = {
    'LEACH': run(LEACH, 200, SEEDS200, m=M, a_mult=A),
    'PEGASIS': run(PEGASIS, 200, SEEDS200, m=M, a_mult=A),
    'SEP': run(SEP, 200, SEEDS200, m=M, a_mult=A),
    'DEEC': run(DEEC, 200, SEEDS200, m=M, a_mult=A),
    'CCH-K3': run(ClusterChainH, 200, SEEDS200, m=M, a_mult=A,
                  mode='multichain', K=3),
}
res['N200'] = {k: window_stats(v) for k, v in ps200.items()}

# ---- 4. first-class relay-K1, heterogeneous N=100 ----
res['het-relay-K1'] = window_stats(
    run(ClusterChainH, 100, SEEDS20, m=M, a_mult=A, mode='relay', K=1))

with open('eval_supplement.json', 'w') as f:
    json.dump(res, f, indent=2)

print(f"{'config':16s} {'LAST':>11s} {'PDR':>6s} {'DELAY':>6s} "
      f"{'1stNorm':>7s} {'1stAdv':>7s}")
for k in ['perclass-K1', 'perclass-K2', 'perclass-K3', 'homo-PEGASIS',
          'homo-CCH-K1', 'homo-relay-K1', 'het-relay-K1']:
    v = res[k]
    fn = f"{v['first_normal'][0]:7.0f}" if 'first_normal' in v else '      -'
    fa = f"{v['first_adv'][0]:7.0f}" if 'first_adv' in v else '      -'
    print(f"{k:16s} {v['LAST'][0]:7.0f}+-{v['LAST'][1]:3.0f} "
          f"{v['PDR'][0]:6.2f} {v['DELAY'][0]:6.1f} {fn} {fa}")
print('--- N=200 heterogeneous ---')
for k, v in res['N200'].items():
    print(f"{k:16s} {v['LAST'][0]:7.0f}+-{v['LAST'][1]:3.0f} "
          f"{v['PDR'][0]:6.2f} {v['DELAY'][0]:6.1f}")
print('Saved eval_supplement.json')
