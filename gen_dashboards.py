"""Regenerate the five dashboard/comparison figures from CURRENT coupled-seed data.

These figures were previously deleted because they were generated (Aug 27) from a
pre-reseed model with a non-existent 'PEGASIS-MST' protocol and stale numbers
(CCH-K3=2884, PEGASIS=1200). This script regenerates them from the SAME model and
seed set as the paper (eval_canonical.json), so every number matches the text.

Protocol set (current repo): LEACH, PEGASIS, SEP, DEEC, DCK-LEACH, NPSOP,
H-PEGASIS (the MST variant — replaces the old 'PEGASIS-MST' label), CCH-K1/K2/K3.
The comparison.png uses the 6 protocols the original figure showed, with
PEGASIS-MST replaced by H-PEGASIS.

All runs use coupled RNG seeding (random + numpy) per seed, MAX_ROUNDS=6000,
N=100, m=0.1, a_mult=2.0, 20 seeds — identical to canonical_eval.py. Re-running is
fast (<2 min) because N=100 with caching.
"""
import json
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from recent_variants import DualHead, PSOCH
from hpegasis import HPEGASIS
from clusterchain_h import ClusterChainH

M, A, N, MAXR, SEEDS = 0.1, 2.0, 100, 6000, [1000 + i * 7 for i in range(20)]

PROTOCOLS = {
    'LEACH': (LEACH, {}),
    'PEGASIS': (PEGASIS, dict(m=M, a_mult=A)),
    'SEP': (SEP, dict(m=M, a_mult=A)),
    'DEEC': (DEEC, dict(m=M, a_mult=A)),
    'DCK-LEACH': (DualHead, dict(m=M, a_mult=A, K=5)),
    'NPSOP': (PSOCH, dict(m=M, a_mult=A, K=5)),
    'H-PEGASIS': (HPEGASIS, dict(m=M, a_mult=A)),
    'CCH-K1': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=1)),
    'CCH-K2': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=2)),
    'CCH-K3': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=3)),
}


def run_all(cls, kw):
    """Return list of 20 histories (each a list of tuples)."""
    out = []
    for s in SEEDS:
        random.seed(s)
        np.random.seed(s)
        out.append(cls(**kw).run(MAXR))
    return out


def metrics(hists):
    lasts, fnds, hnds, pdrs, delays = [], [], [], [], []
    for h in hists:
        last = h[-1][0]
        fnd = next((r[0] for r in h if r[1] < N), last)
        hnd = next((r[0] for r in h if r[1] <= N / 2), last)
        lasts.append(last)
        fnds.append(fnd)
        hnds.append(hnd)
        # PDR / delay use the SAME definition as canonical_eval.py (mean over the
        # first 1500 rounds, PDR capped at 1.0) so the figures match the paper
        # table and eval_canonical.json exactly.
        cap = min(len(h), 1500)
        pdrs.append(np.mean([min(1.0, h[r][3]) for r in range(cap)]))
        delays.append(np.mean([h[r][4] for r in range(cap)]))
    energy = np.mean([np.sum([r[2] for r in h]) for h in hists])
    return {
        'LAST': np.mean(lasts), 'FND': np.mean(fnds), 'HND': np.mean(hnds),
        'PDR': np.mean(pdrs), 'DELAY': np.mean(delays), 'ENERGY': energy,
    }


def alive_curve(hists):
    """Mean alive count per round (align by index 0..min_len)."""
    minlen = min(len(h) for h in hists)
    arr = np.array([[h[i][1] for i in range(minlen)] for h in hists])
    return np.arange(minlen), arr.mean(axis=0)


def energy_curve(hists):
    minlen = min(len(h) for h in hists)
    cum = []
    for h in hists:
        c = np.cumsum([r[2] for r in h[:minlen]])
        cum.append(c)
    return np.arange(minlen), np.mean(cum, axis=0)


print("Running all protocols (coupled-seed, N=100)...")
RAW = {name: run_all(cls, kw) for name, (cls, kw) in PROTOCOLS.items()}
METR = {name: metrics(h) for name, h in RAW.items()}
print("LAST:", {k: round(v['LAST']) for k, v in METR.items()})

# ---- comparison.png : 6-panel bar chart (original 6 protocols, PEGASIS-MST->H-PEGASIS)
comp = ['LEACH', 'PEGASIS', 'SEP', 'DEEC', 'H-PEGASIS', 'CCH-K3']
fig, ax = plt.subplots(2, 3, figsize=(15, 9))
fig.suptitle('Protocol Comparison (N=100, m=0.1, a=2, 20 seeds)', fontsize=14)
panels = [
    ('Network Lifetime (rounds)', 'LAST', 3000),
    ('50% Nodes Dead (rounds)', 'HND', 1500),
    ('Packet Delivery Ratio', 'PDR', 1.0),
    ('End-to-End Delay (hops)', 'DELAY', 100),
    ('Energy-Delay Product (lower better)', None, 130000),
    ('Throughput (PDR)', 'PDR', 1.0),
]
for i, (title, key, ymax) in enumerate(panels):
    r, c = divmod(i, 3)
    vals = []
    for p in comp:
        if key == 'LAST':
            vals.append(METR[p]['LAST'])
        elif key is None:  # EDP proxy = ENERGY * DELAY
            vals.append(METR[p]['ENERGY'] * METR[p]['DELAY'])
        else:
            vals.append(METR[p][key])
    ax[r][c].bar(comp, vals, color=['#1f77b4', '#d62728', '#ff7f0e',
                                     '#9467bd', '#8c564b', '#2ca02c'])
    ax[r][c].set_title(title)
    ax[r][c].set_ylim(0, ymax)
    for j, v in enumerate(vals):
        ax[r][c].text(j, v, f'{v:.0f}' if v > 10 else f'{v:.2f}',
                      ha='center', va='bottom', fontsize=8)
plt.tight_layout()
plt.savefig('comparison.png', dpi=130)
plt.close()

# ---- dashboard.png : LEACH / PEGASIS / CCH-K3, 6 panels
trip = ['LEACH', 'PEGASIS', 'CCH-K3']
fig, ax = plt.subplots(2, 3, figsize=(14, 8))
fig.suptitle('LEACH vs PEGASIS vs ClusterChain-H (N=100, m=0.1, a=2, 20 seeds)',
             fontsize=13)
tp = [
    ('Network Lifetime (rounds)', 'LAST', 3500),
    ('50% Nodes Dead (rounds)', 'HND', 1500),
    ('Alive Nodes over Rounds', 'curve', 100),
    ('Packet Delivery Ratio', 'PDR', 1.0),
    ('Avg End-to-End Delay (hops)', 'DELAY', 100),
    ('Energy x Delay (lower better)', 'exd', None),
]
for i, (title, key, ymax) in enumerate(tp):
    r, c = divmod(i, 3)
    if key == 'curve':
        for p, col in zip(trip, ['#1f77b4', '#d62728', '#2ca02c']):
            x, y = alive_curve(RAW[p])
            ax[r][c].plot(x, y, label=p, color=col)
        ax[r][c].legend(fontsize=8)
        ax[r][c].set_ylim(0, 105)
    else:
        vals = []
        for p in trip:
            if key == 'exd':
                vals.append(METR[p]['ENERGY'] * METR[p]['DELAY'])
            else:
                vals.append(METR[p][key])
        ax[r][c].bar(trip, vals,
                     color=['#1f77b4', '#d62728', '#2ca02c'])
        if ymax:
            ax[r][c].set_ylim(0, ymax)
        for j, v in enumerate(vals):
            ax[r][c].text(j, v, f'{v:.0f}' if v > 10 else f'{v:.2f}',
                          ha='center', va='bottom', fontsize=8)
    ax[r][c].set_title(title)
plt.tight_layout()
plt.savefig('dashboard.png', dpi=130)
plt.close()

# ---- dashboard3.png : lifetime milestones (FND / HND / LAST) for all protocols
order = ['LEACH', 'PEGASIS', 'SEP', 'DEEC', 'DCK-LEACH', 'NPSOP',
         'H-PEGASIS', 'CCH-K1', 'CCH-K2', 'CCH-K3']
fig, ax = plt.subplots(figsize=(13, 6))
x = np.arange(len(order))
w = 0.25
ax.bar(x - w, [METR[p]['FND'] for p in order], w, label='First Death')
ax.bar(x, [METR[p]['HND'] for p in order], w, label='50% Dead')
ax.bar(x + w, [METR[p]['LAST'] for p in order], w, label='Last Dead')
ax.set_xticks(x)
ax.set_xticklabels(order, rotation=30, ha='right', fontsize=8)
ax.set_ylabel('Round')
ax.set_title('Network Lifetime Milestones (N=100, m=0.1, a=2, 20 seeds)')
ax.legend()
plt.tight_layout()
plt.savefig('dashboard3.png', dpi=130)
plt.close()

# ---- death_timeline.png : alive over rounds (LEACH, PEGASIS, CCH-K3)
fig, ax = plt.subplots(figsize=(9, 6))
for p, col in zip(trip, ['#1f77b4', '#d62728', '#2ca02c']):
    x, y = alive_curve(RAW[p])
    ax.plot(x, y, label=f'{p} (lifetime {METR[p]["LAST"]:.0f})', color=col)
ax.set_xlabel('round')
ax.set_ylabel('alive nodes (mean of 20 seeds)')
ax.set_title('Network Lifetime / Node Depletion (N=100, 20 seeds)')
ax.legend()
ax.set_ylim(0, 105)
plt.tight_layout()
plt.savefig('death_timeline.png', dpi=130)
plt.close()

# NOTE: energy_consumption.png and range_impact.png are generated by scenarios.py
# (which correctly uses energy.COMM_RANGE + pdr_early for the R=35m case). Run
# `python scenarios.py` to regenerate those two; this script covers the other
# four comparison/lifetime figures from the same coupled-seed model.

print("Saved comparison.png, dashboard.png, dashboard3.png, death_timeline.png")

