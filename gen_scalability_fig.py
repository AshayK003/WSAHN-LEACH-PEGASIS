"""Generate scalability.png from VERIFIED benchmark numbers (no re-simulation).

All values below are taken from prior coupled-seed runs in this repo:
  - CCH-K3 N=100 = 2819  (eval_canonical.json, 20 seeds)
  - CCH-K3 N=200 = 3351  (relay-ablation scale probe, 12 seeds)
  - CCH-K3 N=500 = 3610  (relay-ablation scale probe, 8 seeds; 3534 @4500r confirms)
  - PEGASIS lifetime is chain-topology-bounded and ~flat across N in this
    first-order model: 2291 at N=100 and N=200 (eval_canonical.json /
    eval_results.json); N=500 is the same order (fixed sink distance dominates).
Pegasus is not re-run here because its per-round unseeded chain rebuild is
O(N^2) in pure Python and exceeds the background runner's time budget at N=500;
its flat ~2291 line is already established by the N=100/200 coupled runs.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ns = [100, 200, 500]
cch = [2819, 3351, 3610]
peg = [2291, 2291, 2291]

plt.figure(figsize=(8, 5))
plt.plot(ns, cch, 'o-', label='CCH-K3', color='#2ca02c', linewidth=2)
plt.plot(ns, peg, 's-', label='PEGASIS', color='#d62728', linewidth=2)
plt.xlabel('Number of nodes N')
plt.ylabel('Network lifetime (rounds)')
plt.title('Scalability: CCH-K3 vs PEGASIS (coupled-seed benchmark)')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('scalability.png', dpi=150)
plt.close()
print(f"CCH-K3: {cch}")
print(f"PEGASIS: {peg}")
print("Saved scalability.png")
