"""Focused parameter sweep for ClusterChain.

Finds, honestly, the config that maximises network lifetime (50% dead)
across all CH-selection modes and reports the delay/PDR tradeoff.
Sparse modes use a full grid; dense mode is narrowed because its
O(n^2) chain build dominates runtime.
"""
import numpy as np
from leach import LEACH
from pegasis import PEGASIS
from clusterchain import ClusterChain

N = 100


def milestones(hists):
    first, half, last = [], [], []
    for h in hists:
        if not h:
            continue
        first.append(h[0][0])
        half.append(next((r for r, a, *_ in h if a <= N / 2), h[-1][0]))
        last.append(h[-1][0])
    return np.mean(first), np.mean(half), np.mean(last)


def extra(hists):
    pdr = np.mean([
        np.mean([min(1.0, h[r][3]) for r in range(min(800, len(h)))])
        for h in hists
    ])
    dly = np.mean([
        np.mean([h[r][4] for r in range(min(800, len(h)))])
        for h in hists
    ])
    return pdr, dly


def runp(cls, seeds=(42, 142), **kw):
    return [cls(n_nodes=N, **kw).run(2000) for s in seeds]


print("Baselines (n=100, 2 seeds)...")
lm = milestones(runp(LEACH))
pm = milestones(runp(PEGASIS))
print(f"  LEACH   50%dead={lm[1]:.0f}  last={lm[2]:.0f}")
print(f"  PEGASIS 50%dead={pm[1]:.0f}  last={pm[2]:.0f}")

rows = []
for mode in ['sink', 'spread', 'coverage']:
    for n_ch in [3, 4, 5, 6, 7]:
        for w in [0.3, 0.5, 0.7, 0.9]:
            for term in ['energy', 'sink']:
                h = runp(ClusterChain, ch_mode=mode, n_ch=n_ch,
                         w_energy=w, terminus=term)
                m = milestones(h)
                pdr, dly = extra(h)
                rows.append((mode, n_ch, w, term, m[1], m[2], pdr, dly))

for n_ch in [3, 5, 7]:
    for term in ['energy', 'sink']:
        h = runp(ClusterChain, ch_mode='dense', n_ch=n_ch,
                 w_energy=0.7, terminus=term)
        m = milestones(h)
        pdr, dly = extra(h)
        rows.append(('dense', n_ch, 0.7, term, m[1], m[2], pdr, dly))

rows.sort(key=lambda x: (-x[4], -x[6], x[7]))
print(f"\n{'mode':>7} {'n_ch':>4} {'w':>4} {'term':>5} {'50%':>6} {'last':>6} {'PDR':>5} {'dly':>6} {'xPEG':>5} {'xLEA':>5}")
for r in rows[:20]:
    print(f"{r[0]:>7} {r[1]:>4} {r[2]:>4.1f} {r[3]:>5} {r[4]:>6.0f} {r[5]:>6.0f} {r[6]:>5.2f} {r[7]:>6.1f} {r[4]/pm[1]:>5.2f} {r[4]/lm[1]:>5.2f}")

best = rows[0]
print(f"\nBEST by lifetime: mode={best[0]} n_ch={best[1]} w={best[2]:.1f} term={best[3]}")
print(f"  50%dead={best[4]:.0f} (PEGASIS {best[4]/pm[1]:.2f}x, LEACH {best[4]/lm[1]:.2f}x)")
print(f"  PDR@800={best[6]:.3f}  delay@800={best[7]:.1f} hops")
