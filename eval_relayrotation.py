"""A/B test 4: relay ROTATION vs static budgeted relay.

Question: does rotating the relay role (instead of fixing it on two 0.5J nodes)
keep PDR high past round 341, where the static budgeted relay died and
collapsed PDR to 0.19?

Configs (all budgeted 0.5J, K=1, 20 seeds, coupled RNG, MAX_ROUNDS=6000):
  - Static (rotate_every=None):  expect PDR collapse after relay dies @341
  - Rotate every 25/50/100 rounds:  expect PDR to stay high (cost spread)

Key metric: PDR over rounds > 341 (mean of self.pdr_after_341) -- this is the
delivery behaviour the static design failed to preserve.
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


protos = {
    'CCH-K1 (baseline)':            run(ClusterChainH, 100, SEEDS, m=M, a_mult=A,
                                        mode='multichain', K=1),
    'Static budgeted (no rot)':     run(RelayRotationClusterChain, 100, SEEDS, m=M,
                                        a_mult=A, K=1, relay_energy=0.5,
                                        rotate_every=None),
    'Rotate every 25':              run(RelayRotationClusterChain, 100, SEEDS, m=M,
                                        a_mult=A, K=1, relay_energy=0.5,
                                        rotate_every=25),
    'Rotate every 50':              run(RelayRotationClusterChain, 100, SEEDS, m=M,
                                        a_mult=A, K=1, relay_energy=0.5,
                                        rotate_every=50),
    'Rotate every 100':             run(RelayRotationClusterChain, 100, SEEDS, m=M,
                                        a_mult=A, K=1, relay_energy=0.5,
                                        rotate_every=100),
}

result = {}
for k, ps in protos.items():
    last = [p.history[-1][0] for p in ps]
    censored = sum(1 for L in last if L >= MAX_ROUNDS)
    fnd = [min(r for r, a, *_ in p.history if a < 100) for p in ps]
    pdr = [np.mean([min(1.0, p.history[r][3]) for r in range(min(len(p.history), 2000))])
           for p in ps]
    # PDR over the post-341 window: mean across seeds of each protocol's
    # pdr_after_341 list (or empty -> flag)
    post = [float(np.mean(getattr(p, 'pdr_after_341', []))) if getattr(p, 'pdr_after_341', None) else float('nan')
            for p in ps]
    dead = [getattr(p, 'relay_dead_round', None) for p in ps]
    result[k] = {'LAST': ci(last), 'CEN': censored, 'FND': ci(fnd),
                 'PDR': ci(pdr), 'PDR_post341': float(np.nanmean(post)),
                 'RELAY_DEAD': [d for d in dead if d is not None]}

with open('eval_relayrotation.json', 'w') as f:
    json.dump(result, f, indent=2)

base = result['CCH-K1 (baseline)']['LAST'][0]
print(f'{"protocol":26s} {"LAST":>6s} {"xPEG":>5s} {"CEN":>4s} {"PDR":>5s} '
      f'{"PDR>341":>7s} {"RelayDead":>9s}')
for k in protos:
    m, c = result[k]['LAST']
    rd = result[k]['RELAY_DEAD']
    rd_s = str(rd[0]) if rd else '-'
    p341 = result[k]['PDR_post341']
    p341_s = f'{p341:7.2f}' if p341 == p341 else '   n/a'
    print(f'{k:26s} {m:6.0f}±{c:3.0f} {m/base:5.2f} {result[k]["CEN"]:4d} '
          f'{result[k]["PDR"][0]:5.2f} {p341_s} {rd_s:>9s}')
