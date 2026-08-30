"""A/B test: do energy-gradient relay + adaptive-K actually beat the current
ClusterChain-H multichain K=1 (the lifetime-optimal baseline)?

All protocols share energy.py and the identical heterogeneous deployment
(m=0.1, a_mult=2.0, 100 nodes, sink at (50,175), 4000-bit packets, 20 seeds).
Reporting FND / LAST / PDR / hop-delay / Energy×Delay so a lifetime "win" that
sacrifices delivery or balloons delay is caught.
"""
import json
import numpy as np
from clusterchain_h import ClusterChainH
from cch_experimental import ClusterChainExpt

M, A = 0.1, 2.0
MAX_ROUNDS = 4000
SEEDS = [1000 + i * 7 for i in range(20)]


def run(cls, n, seeds, **kw):
    out = []
    for s in seeds:
        # Seed BOTH RNGs so every protocol sees the IDENTICAL node topology for a
        # given seed (ClusterChainH.__init__ draws positions via random.uniform).
        # Without random.seed the cross-protocol comparison is only valid in
        # expectation, not like-for-like.
        import random as _r
        _r.seed(s)
        np.random.seed(s)
        out.append(cls(n_nodes=n, **kw).run(MAX_ROUNDS))
    return out


def ci(arr):
    arr = np.asarray(arr, float)
    return float(arr.mean()), float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr)))


# Baseline = current lifetime-optimal. Variants test ONE mechanism at a time.
protos = {
    'CCH-K1 (baseline)':   run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                               mode='multichain', K=1),
    'CCH-K3 (delay ref)':  run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                               mode='multichain', K=3),
    'EG-K1 (relay only)':  run(ClusterChainExpt, 100, SEEDS, m=M, a_mult=A,
                               mode='multichain', K=1, eg_relay=True,
                               adaptive_k_expt=False),
    'EG-ADP (relay+K)':    run(ClusterChainExpt, 100, SEEDS, m=M, a_mult=A,
                               mode='multichain', K=5, eg_relay=True,
                               adaptive_k_expt=True),
}

result = {}
for k, hists in protos.items():
    last = [h[-1][0] for h in hists]
    fnd = [min(r for r, a, *_ in h if a < 100) for h in hists]
    pdr = [np.mean([min(1.0, h[r][3]) for r in range(min(len(h), 1500))]) for h in hists]
    dly = [np.mean([h[r][4] for r in range(min(len(h), 1500))]) for h in hists]
    # Energy×Delay proxy: mean per-round tx+rx energy * mean delay over first 1500 rounds
    ed = [np.mean([h[r][2] * h[r][4] for r in range(min(len(h), 1500))]) for h in hists]
    result[k] = {'LAST': ci(last), 'FND': ci(fnd), 'PDR': ci(pdr),
                 'DELAY': ci(dly), 'EXD': ci(ed)}

with open('eval_experimental.json', 'w') as f:
    json.dump(result, f, indent=2)

base = result['CCH-K1 (baseline)']['LAST'][0]
print(f'{"protocol":20s} {"LAST":>7s} {"CI":>6s} {"xPEG":>5s} {"FND":>6s} '
      f'{"PDR":>5s} {"DLY":>6s} {"ExD":>9s}')
for k in protos:
    m, c = result[k]['LAST']
    print(f'{k:20s} {m:7.0f} ±{c:4.0f} {m/base:5.2f} {result[k]["FND"][0]:6.0f} '
          f'{result[k]["PDR"][0]:5.2f} {result[k]["DELAY"][0]:6.1f} '
          f'{result[k]["EXD"][0]:9.2e}')
