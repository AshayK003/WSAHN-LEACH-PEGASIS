"""Extra evaluation scenarios for the mini-project guidelines:

  1. Communication-range sensitivity (guideline 4/5/6): demonstrate that the
     configurable COMM_RANGE parameter produces range-induced packet loss.
     Compares PDR at unlimited range vs a finite R = 35 m for the three
     protocols. Lifetime is unaffected (out-of-range attempts still spend
     energy), isolating the packet-loss effect.

  2. Energy consumption (guideline 6): plots mean cumulative energy consumed
     over rounds for LEACH / PEGASIS / ClusterChain-H.

Outputs: range_impact.png, energy_consumption.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import energy
from leach import LEACH
from pegasis import PEGASIS
from clusterchain_h import ClusterChainH

SEEDS = [1000 + i * 7 for i in range(15)]
N = 100
M, A = 0.1, 2.0
MAXR = 4000

PROTOS = {
    "LEACH": (LEACH, {}),
    "PEGASIS": (PEGASIS, {}),
    "ClusterChain-H": (ClusterChainH, dict(mode="multichain", K=3, m=M, a_mult=A)),
}


def run(cls, rng, **kw):
    out = []
    for s in SEEDS:
        energy.COMM_RANGE = rng
        np.random.seed(s)
        out.append(cls(n_nodes=N, **kw).run(MAXR))
    return out


def pdr_early(hists):
    return float(np.mean([np.mean([min(1.0, h[r][3]) for r in range(min(len(h), 1500))])
                         for h in hists]))


def cum_energy(hists):
    maxr = max(len(h) for h in hists)
    cum = np.zeros(maxr)
    for h in hists:
        c = np.cumsum([hh[2] for hh in h])
        cum[: len(c)] += c
        cum[len(c):] += c[-1]
    return cum / len(hists)


# ---- run both ranges + cumulative energy ----
results = {}
cum = {}
for name, (cls, kw) in PROTOS.items():
    hu = run(cls, None, **kw)
    hr = run(cls, 35.0, **kw)
    results[(name, None)] = pdr_early(hu)
    results[(name, 35.0)] = pdr_early(hr)
    cum[name] = cum_energy(hu)

# ---- range_impact.png ----
fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(PROTOS))
w = 0.36
u = [results[(p, None)] for p in PROTOS]
l = [results[(p, 35.0)] for p in PROTOS]
ax.bar(x - w / 2, u, w, label="Unlimited range", color="#2ca02c")
ax.bar(x + w / 2, l, w, label="R = 35 m", color="#d62728")
for i, (a, b) in enumerate(zip(u, l)):
    ax.text(i - w / 2, a + 0.02, f"{a:.2f}", ha="center", fontsize=8)
    ax.text(i + w / 2, b + 0.02, f"{b:.2f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(list(PROTOS.keys()))
ax.set_ylabel("Packet Delivery Ratio (early)")
ax.set_ylim(0, 1.15); ax.legend()
ax.set_title("Effect of Communication Range on PDR\n(range-limited links drop packets; lifetime unchanged)")
plt.tight_layout(); plt.savefig("range_impact.png", dpi=150); plt.close()

# ---- energy_consumption.png ----
fig, ax = plt.subplots(figsize=(9, 5.5))
colors = {"LEACH": "#1f77b4", "PEGASIS": "#d62728", "ClusterChain-H": "#2ca02c"}
for name in PROTOS:
    y = cum[name]
    ax.plot(np.arange(len(y)), y, label=name, color=colors[name], lw=2)
ax.set_xlabel("round"); ax.set_ylabel("Cumulative energy consumed (J, mean of 15 seeds)")
ax.set_title("Network Energy Consumption over Time")
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout(); plt.savefig("energy_consumption.png", dpi=150); plt.close()

print("Saved range_impact.png, energy_consumption.png")
for name in PROTOS:
    print(f"  {name:14s} PDR unlimited={results[(name, None)]:.3f}  "
          f"PDR R=35m={results[(name, 35.0)]:.3f}  "
          f"loss@35m={(1-results[(name, 35.0)]):.3f}")
