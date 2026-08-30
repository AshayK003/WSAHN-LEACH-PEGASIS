"""A/B test 3: static relay-sink tier vs baseline multichain K=1.

Honest two-mode relay test (review's highest-upside candidate, minus mobility
accounting -- the lower-risk "static relay tier" version):
  - UNLIMITED relay  : infrastructure subsidy NOT charged (max geometric upside)
  - BUDGETED 0.5J    : per-relay battery == one sensor node (subsidy removed)
                        -> if the relay dies, chains fall back to direct BS and
                           relay_dead_round is recorded.

Fairness: terminus->relay is charged to the SENSOR exactly like baseline's
terminus->BS. Relay->BS forward is infrastructure, tracked separately
(self.relay_forward_total) and never folded into sensor energy.

All share energy.py + identical deployment (m=0.1, a_mult=2.0, 100 nodes,
20 seeds, BOTH RNGs seeded so topologies are like-for-like). MAX_ROUNDS is
raised to 6000 so relay variants (which extend lifetime) are measured, not
capped; a run that hits the cap is flagged as "censored" (lower bound only).
"""
import json
import numpy as np
from clusterchain_h import ClusterChainH
from cch_relaysink import RelaySinkClusterChain

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


protos = {
    'CCH-K1 (baseline)':          run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                                     mode='multichain', K=1),
    'Relay-UNLIMITED (K=1)':      run(RelaySinkClusterChain, 100, SEEDS, m=M, a_mult=A,
                                     K=1, relay_energy=None),
    'Relay-BUDGETED 0.5J (K=1)':  run(RelaySinkClusterChain, 100, SEEDS, m=M, a_mult=A,
                                     K=1, relay_energy=0.5),
}

result = {}
for k, ps in protos.items():
    last = [p.history[-1][0] for p in ps]
    censored = sum(1 for L in last if L >= MAX_ROUNDS)
    fnd = [min(r for r, a, *_ in p.history if a < 100) for p in ps]
    pdr = [np.mean([min(1.0, p.history[r][3]) for r in range(min(len(p.history), 2000))])
           for p in ps]
    dly = [np.mean([p.history[r][4] for r in range(min(len(p.history), 2000))])
           for p in ps]
    relay_infra = [getattr(p, 'relay_forward_total', 0.0) for p in ps]
    dead = [getattr(p, 'relay_dead_round', None) for p in ps]
    result[k] = {'LAST': ci(last), 'CENSORED': censored, 'FND': ci(fnd),
                 'PDR': ci(pdr), 'DELAY': ci(dly),
                 'RELAY_INFRA': float(np.mean(relay_infra)),
                 'RELAY_DEAD_ROUND': [d for d in dead if d is not None]}

with open('eval_relaysink.json', 'w') as f:
    json.dump(result, f, indent=2)

base = result['CCH-K1 (baseline)']['LAST'][0]
print(f'{"protocol":24s} {"LAST":>6s} {"xPEG":>5s} {"CEN":>4s} {"FND":>5s} '
      f'{"PDR":>5s} {"DLY":>5s} {"RelayInfra":>10s} {"RelayDead":>9s}')
for k in protos:
    m, c = result[k]['LAST']
    rd = result[k]['RELAY_DEAD_ROUND']
    rd_s = str(rd[0]) if rd else '-'
    print(f'{k:24s} {m:6.0f}±{c:3.0f} {m/base:5.2f} {result[k]["CENSORED"]:4d} '
          f'{result[k]["FND"][0]:5.0f} {result[k]["PDR"][0]:5.2f} '
          f'{result[k]["DELAY"][0]:5.1f} {result[k]["RELAY_INFRA"]:10.2f} {rd_s:>9s}')
