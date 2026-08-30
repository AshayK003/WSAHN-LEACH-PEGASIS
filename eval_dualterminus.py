"""A/B test 2: does Selective Dual-Terminus actually help ClusterChain-H?

All protocols share energy.py and the identical heterogeneous deployment
(m=0.1, a_mult=2.0, 100 nodes, sink at (50,175), 4000-bit packets, 20 seeds).
Reporting LAST / FND / PDR / delay / Energy×Delay AND per-class first-death
(normal vs advanced) so we can see whether the redundancy favours one class.

Dual-terminus here is FAIL-OVER only: a vice node is added to chains longer
than a threshold and pays a sink hop ONLY when the primary terminus would have
died on that hop (recovering the round instead of clearing the chain).
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


protos = {
    'CCH-K1 (baseline)':    run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                                mode='multichain', K=1),
    'CCH-K3 (delay ref)':   run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                                mode='multichain', K=3),
    'DT-K1 (dual, K=1)':    run(ClusterChainExpt, 100, SEEDS, m=M, a_mult=A,
                                mode='multichain', K=1, dual_terminus=True),
    'DT-K3 (dual, K=3)':    run(ClusterChainExpt, 100, SEEDS, m=M, a_mult=A,
                                mode='multichain', K=3, dual_terminus=True),
}

result = {}
for k, ps in protos.items():
    last = [p.history[-1][0] for p in ps]
    fnd = [min(r for r, a, *_ in p.history if a < 100) for p in ps]
    # per-class first death for normal nodes and advanced nodes
    fnd_norm = []
    fnd_adv = []
    for p in ps:
        ch = getattr(p, 'class_history', None)
        if ch is None:
            fnd_norm.append(last[len(fnd_norm)])
            fnd_adv.append(last[len(fnd_adv)])
            continue
        fn = min((r for r, av, nm in ch if nm < p.n - int(round(M * p.n))),
                 default=None)
        fa = min((r for r, av, nm in ch if av < int(round(M * p.n))),
                 default=None)
        fnd_norm.append(fn if fn is not None else p.history[-1][0])
        fnd_adv.append(fa if fa is not None else p.history[-1][0])
    pdr = [np.mean([min(1.0, p.history[r][3]) for r in range(min(len(p.history), 1500))])
           for p in ps]
    dly = [np.mean([p.history[r][4] for r in range(min(len(p.history), 1500))])
           for p in ps]
    ed = [np.mean([p.history[r][2] * p.history[r][4] for r in range(min(len(p.history), 1500))])
          for p in ps]
    result[k] = {'LAST': ci(last), 'FND': ci(fnd),
                 'FND_norm': ci(fnd_norm), 'FND_adv': ci(fnd_adv),
                 'PDR': ci(pdr), 'DELAY': ci(dly), 'EXD': ci(ed)}

with open('eval_dualterminus.json', 'w') as f:
    json.dump(result, f, indent=2)

base = result['CCH-K1 (baseline)']['LAST'][0]
print(f'{"protocol":20s} {"LAST":>6s} {"xPEG":>5s} {"FND":>5s} {"PDR":>5s} '
      f'{"DLY":>5s} {"ExD":>8s} {"FNDn":>5s} {"FNDa":>5s}')
for k in protos:
    m, c = result[k]['LAST']
    print(f'{k:20s} {m:6.0f} {m/base:5.2f} {result[k]["FND"][0]:5.0f} '
          f'{result[k]["PDR"][0]:5.2f} {result[k]["DELAY"][0]:5.1f} '
          f'{result[k]["EXD"][0]:8.2e} {result[k]["FND_norm"][0]:5.0f} '
          f'{result[k]["FND_adv"][0]:5.0f}')
