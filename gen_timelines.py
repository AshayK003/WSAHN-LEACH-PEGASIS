"""Timeline diagrams: per-round metric curves over the network lifetime.

Complements the milestone bar figures (comparison/dashboard/dashboard3) with
time-series panels: alive nodes, PDR, throughput, end-to-end delay,
energy-per-round and cumulative energy — each as the mean over the same 20
coupled seeds (N=100, heterogeneous m=0.1/a=2.0, both RNGs seeded) used by
canonical_eval.py, so every curve matches the paper tables.

Protocols: LEACH, PEGASIS, SEP, DEEC, CCH-K1 (lifetime-optimal), CCH-K3
(low-delay). Curves are averaged per round over the histories alive at that
round (same convention as run.py); the x-axis therefore spans the full
lifetime of the longest-lived protocol.

Output: timelines.png (6-panel overview).
Run:  python gen_timelines.py   (a few minutes, N=100 only)
"""
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH

M, A, N, MAXR = 0.1, 2.0, 100, 6000
SEEDS = [1000 + i * 7 for i in range(20)]

PROTOCOLS = {
    'LEACH': (LEACH, dict(m=M, a_mult=A)),
    'PEGASIS': (PEGASIS, dict(m=M, a_mult=A)),
    'SEP': (SEP, dict(m=M, a_mult=A)),
    'DEEC': (DEEC, dict(m=M, a_mult=A)),
    'CCH-K1': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=1)),
    'CCH-K3': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=3)),
}
COLORS = {
    'LEACH': '#1f77b4', 'PEGASIS': '#d62728', 'SEP': '#ff7f0e',
    'DEEC': '#9467bd', 'CCH-K1': '#2ca02c', 'CCH-K3': '#8c564b',
}


def run_all(cls, kw):
    out = []
    for s in SEEDS:
        random.seed(s)
        np.random.seed(s)
        out.append(cls(n_nodes=N, **kw).run(MAXR))
    return out


def mean_curve(hists, idx, transform=None):
    """Mean per-round series of history field `idx` over runs alive that round."""
    maxr = max(len(h) for h in hists)
    xs, ys = [], []
    for r in range(maxr):
        vals = [h[r][idx] for h in hists if r < len(h)]
        if not vals:
            break
        v = float(np.mean(vals))
        ys.append(transform(v) if transform else v)
        xs.append(r + 1)
    return np.array(xs), np.array(ys)


def alive_curve_all(hists):
    """Mean alive count per round over ALL seeds (ended runs count as 0) — so
    the tail cannot jump back up when only a few long-lived runs remain."""
    maxr = max(len(h) for h in hists)
    xs = np.arange(1, maxr + 1)
    ys = np.array([np.mean([h[r][1] if r < len(h) else 0 for h in hists])
                   for r in range(maxr)], dtype=float)
    return xs, ys


def smooth(y, window=25):
    """Light centered moving average for readability (milestone tables in the
    paper use the raw unsmoothed means). Edge-padded so round 1 has no ramp
    artifact."""
    if len(y) < window:
        return y
    k = np.ones(window) / window
    ypad = np.pad(y, window // 2, mode='edge')
    return np.convolve(ypad, k, mode='valid')[:len(y)]


def throughput_curve(hists):
    maxr = max(len(h) for h in hists)
    xs, ys = [], []
    for r in range(maxr):
        vals = [h[r][6] / max(1, h[r][5]) for h in hists if r < len(h)]
        if not vals:
            break
        xs.append(r + 1)
        ys.append(float(np.mean(vals)))
    return np.array(xs), np.array(ys)


print("Running timeline simulations (coupled-seed, N=100)...")
RAW = {}
for name, (cls, kw) in PROTOCOLS.items():
    print(f"  {name} ...", flush=True)
    RAW[name] = run_all(cls, kw)
print("LAST (mean):", {k: round(float(np.mean([len(h) for h in v]))) for k, v in RAW.items()})

fig, ax = plt.subplots(2, 3, figsize=(17, 10))
fig.suptitle('Metric Timelines over Network Lifetime (N=100, m=0.1, a=2, 20 seeds)',
             fontsize=14, fontweight='bold')

panels = [
    (0, 0, 'Alive Nodes over Rounds', 'alive nodes', None, (0, 105)),
    (0, 1, 'Packet Delivery Ratio over Rounds', 'PDR', None, (0, 1.05)),
    (0, 2, 'Throughput over Rounds', 'delivered / sent', None, (0, 1.05)),
    (1, 0, 'End-to-End Delay over Rounds', 'delay (hops)', None, None),
    (1, 1, 'Energy per Round', 'energy (J/round)', None, None),
    (1, 2, 'Cumulative Energy Consumed', 'cumulative energy (J)', 'cumsum', None),
]

for r, c, title, ylab, mode, ylim in panels:
    a = ax[r][c]
    for name in PROTOCOLS:
        if mode == 'cumsum':
            x, y = mean_curve(RAW[name], 2)
            y = np.cumsum(y)
        elif title.startswith('Throughput'):
            x, y = throughput_curve(RAW[name])
            y = smooth(y)
        elif title.startswith('Alive'):
            x, y = alive_curve_all(RAW[name])
        elif title.startswith('Packet Delivery'):
            x, y = mean_curve(RAW[name], 3)
            y = smooth(y)
        elif title.startswith('End-to-End'):
            x, y = mean_curve(RAW[name], 4)
            y = smooth(y)
        else:  # Energy per Round
            x, y = mean_curve(RAW[name], 2)
            y = smooth(y)
        a.plot(x, y, label=name, color=COLORS[name], linewidth=1.8)
    a.set_title(title)
    a.set_xlabel('round')
    a.set_ylabel(ylab)
    a.legend(fontsize=8)
    a.grid(True, alpha=0.3)
    if ylim:
        a.set_ylim(*ylim)

plt.tight_layout()
plt.savefig('timelines.png', dpi=150)
plt.close()
print("Saved timelines.png")
