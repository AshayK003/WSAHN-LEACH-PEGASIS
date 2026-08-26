"""Focused LEACH vs PEGASIS vs ClusterChain-H dashboard + death timeline.

Generates:
  dashboard3.png     - 2x3 grid: lifetime, HND, death-timeline, PDR, delay, E x D
  death_timeline.png - alive-nodes-over-rounds (mean) for the 3 protocols
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from leach import LEACH
from pegasis import PEGASIS
from clusterchain_h import ClusterChainH

M, A, MAXR = 0.1, 2.0, 4000
SEEDS = [1000 + i * 7 for i in range(20)]
N = 100


def run(cls, **kw):
    out = []
    for s in SEEDS:
        np.random.seed(s)
        out.append(cls(n_nodes=N, **kw).run(MAXR))
    return out


def summarize(hists):
    last = np.mean([h[-1][0] for h in hists if h])
    hnd = np.mean([next((r for r, a, *_ in h if a <= N / 2), h[-1][0]) for h in hists if h])
    pdr = np.mean([float(np.mean([min(1.0, h[r][3]) for r in range(min(len(h), 1500))])) for h in hists])
    dly = np.mean([float(np.mean([h[r][4] for r in range(min(len(h), 1500))])) for h in hists])
    maxr = max(len(h) for h in hists)
    alive = np.zeros(maxr)
    for h in hists:
        for r in range(len(h)):
            alive[r] += h[r][1]
        alive[len(h):] += 0
    alive /= len(hists)
    return {"LAST": last, "HND": hnd, "PDR": pdr, "DELAY": dly, "ALIVE": alive}


protos = {
    "LEACH": run(LEACH),
    "PEGASIS": run(PEGASIS),
    "ClusterChain-H": run(ClusterChainH, mode="multichain", K=3, m=M, a_mult=A),
}
data = {k: summarize(v) for k, v in protos.items()}
order = ["LEACH", "PEGASIS", "ClusterChain-H"]
colors = {"LEACH": "#1f77b4", "PEGASIS": "#d62728", "ClusterChain-H": "#2ca02c"}

# ---------- dashboard3.png ----------
fig, ax = plt.subplots(2, 3, figsize=(15, 9))
fig.suptitle("LEACH  vs  PEGASIS  vs  ClusterChain-H   (N=100, m=0.10, a=2.0, 20 seeds)",
             fontsize=14, fontweight="bold")

# lifetime
ax[0, 0].bar(order, [data[k]["LAST"] for k in order], color=[colors[k] for k in order], edgecolor="k")
ax[0, 0].set_title("Network Lifetime (last node dead)")
ax[0, 0].set_ylabel("rounds")
for i, k in enumerate(order):
    ax[0, 0].text(i, data[k]["LAST"] + 20, f'{data[k]["LAST"]:.0f}', ha="center", fontsize=9)

# HND
ax[0, 1].bar(order, [data[k]["HND"] for k in order], color=[colors[k] for k in order], edgecolor="k")
ax[0, 1].set_title("50% Nodes Dead (HND)")
ax[0, 1].set_ylabel("round")
for i, k in enumerate(order):
    ax[0, 1].text(i, data[k]["HND"] + 20, f'{data[k]["HND"]:.0f}', ha="center", fontsize=9)

# death timeline
for k in order:
    ax[0, 2].plot(data[k]["ALIVE"], label=k, color=colors[k], lw=2)
ax[0, 2].set_title("Alive Nodes over Rounds")
ax[0, 2].set_xlabel("round"); ax[0, 2].set_ylabel("alive nodes")
ax[0, 2].legend(); ax[0, 2].set_ylim(0, N + 5)

# PDR (drop rate = 1 - PDR)
ax[1, 0].bar(order, [data[k]["PDR"] for k in order], color=[colors[k] for k in order], edgecolor="k")
ax[1, 0].set_title("Packet Delivery Ratio (PDR)")
ax[1, 0].set_ylabel("PDR"); ax[1, 0].set_ylim(0, 1.1)
for i, k in enumerate(order):
    ax[1, 0].text(i, data[k]["PDR"] + 0.02, f'{data[k]["PDR"]:.2f}', ha="center", fontsize=9)

# delay
ax[1, 1].bar(order, [data[k]["DELAY"] for k in order], color=[colors[k] for k in order], edgecolor="k")
ax[1, 1].set_title("Avg End-to-End Delay")
ax[1, 1].set_ylabel("hops")
for i, k in enumerate(order):
    ax[1, 1].text(i, data[k]["DELAY"] + 1, f'{data[k]["DELAY"]:.1f}', ha="center", fontsize=9)

# E x D
ed = {k: data[k]["LAST"] * data[k]["DELAY"] for k in order}
ax[1, 2].bar(order, [ed[k] for k in order], color=[colors[k] for k in order], edgecolor="k")
ax[1, 2].set_title("Energy x Delay (lower better)")
ax[1, 2].set_ylabel("E x D")
for i, k in enumerate(order):
    ax[1, 2].text(i, ed[k] + 0.02, f'{ed[k]:.3f}', ha="center", fontsize=9)

for a in ax.flat:
    a.grid(True, alpha=0.3, axis="y")
plt.tight_layout()
plt.savefig("dashboard3.png", dpi=150)
plt.close()

# ---------- death_timeline.png ----------
fig, ax = plt.subplots(figsize=(9, 5.5))
for k in order:
    ax.plot(data[k]["ALIVE"], label=f'{k} (lifetime {data[k]["LAST"]:.0f})', color=colors[k], lw=2.2)
ax.set_title("Network Death Timeline: Alive Nodes vs Round", fontsize=13, fontweight="bold")
ax.set_xlabel("round"); ax.set_ylabel("alive nodes (mean of 20 seeds)")
ax.set_ylim(0, N + 5); ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("death_timeline.png", dpi=150)
plt.close()

print("Saved dashboard3.png, death_timeline.png")
for k in order:
    print(f"  {k:14s} LAST={data[k]['LAST']:.0f}  HND={data[k]['HND']:.0f}  "
          f"PDR={data[k]['PDR']:.3f}  DELAY={data[k]['DELAY']:.1f}  ExD={ed[k]:.3f}")
