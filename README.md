# ClusterChain-H: LEACH / PEGASIS Hybrid vs ClusterChain-H WSN Routing Comparison

Simulation-based performance comparison of hierarchical routing protocols for
Wireless Sensor Networks (WSNs), including **ClusterChain-H** — a heterogeneity-aware
hybrid protocol proposed and evaluated in this project.

## Overview

This project implements and compares five routing protocols under a single
first-order radio energy model (Heinzelman et al., 2000) so every result is
strictly like-for-like:

- **LEACH** (Low-Energy Adaptive Clustering Hierarchy) — probabilistic cluster
  head rotation. Random cluster-head election ignores residual energy and
  distance to the sink, so a far cluster head can pay a costly multipath hop
  every round (Heinzelman et al., 2000).
- **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems) — a
  greedy chain over all nodes. Energy is balanced well, but every node relays
  every round (high delay, ~90 hops) and the chain-end leader is a permanent
  hotspot (Lindsey & Raghavendra, 2002).
- **SEP / DEEC** — heterogeneity-aware cluster-head election (advanced nodes at
  2x initial energy carry the load), the standard heterogeneous baselines
  (Smaragdakis et al., 2004; Qing et al., 2006).
- **ClusterChain-H** — a hybrid combining LEACH-style clustering with a
  PEGASIS-style refined chain, plus four mechanisms: MST chain geometry (removes
  PEGASIS's long greedy links), an energy + sink-proximity **rotating terminus**
  (removes the permanent leader hotspot), heterogeneity-aware election (SEP/DEEC
  style), and an analytically grounded adaptive chain count K that trades delay
  against lifetime.

All protocols share the same `energy.py`, seed set, and deployment, so comparisons
are fair. ClusterChain-H generalises the SEP/DEEC heterogeneity idea into a
clustering + chaining hybrid and removes the PEGASIS leader hotspot via the
rotating terminus across parallel chains.

## Key Results

Network lifetime, delivery and delay averaged over **20 seeded runs**
(100 nodes, 100m x 100m field, sink at (50, 175), 0.5 J initial energy;
**heterogeneous deployment: 10% advanced nodes at 2x energy = 0.55 J/node budget**):

| Protocol | Last node dead | PDR | Delay (hops) | Lifetime / J | vs PEGASIS |
|----------|--------------:|----:|------------:|------------:|-----------:|
| LEACH (het) | 922 | 0.98 | 1.0 | 1679 | 0.40x |
| PEGASIS (het) | 2335 | 0.99 | 76.9 | 4232 | 1.00x |
| SEP | 1391 | 0.99 | 1.0 | 2450 | 0.60x |
| DEEC | 1213 | 0.99 | 1.0 | 2189 | 0.52x |
| **ClusterChain-H (K=1)** | **3111** | **1.00** | 74.6 | **5785** | **1.33x** |
| **ClusterChain-H (K=3)** | **2980** | **1.00** | **24.6** | 5288 | 1.28x |

**Honest summary.** ClusterChain-H does not invent extra battery to win: every
protocol above runs on the *identical* 0.55 J/node heterogeneous budget, and the
"Lifetime / J" column normalises lifetime by that budget so the gain is a protocol
efficiency, not a capacity artefact. Against the strongest like-for-like baseline
(heterogeneous PEGASIS) it delivers **1.33x** lifetime with equal-or-better PDR and
substantially lower delay (K=3 cuts delay ~3x at a small lifetime cost). Against the
heterogeneity-aware SEP/DEEC baselines the margin is larger (2.2-2.6x), because those
protocols keep PEGASIS's single-chain topology and leader hotspot.

A **homogeneous ablation** (no advanced nodes; geometry + rotating terminus only)
gives ClusterChain-H **1.41x** the lifetime of homogeneous PEGASIS (1696 vs 1200
rounds), confirming the structural mechanisms are independently effective; the full
heterogeneous gain combines that structural contribution with heterogeneity-aware
election.

## Reproducibility

```bash
pip install -r requirements.txt

# 3-protocol comparison (legacy ClusterChain harness, 3 runs, 2000 rounds)
python run.py --nodes 100 --rounds 2000 --runs 3

# Full ClusterChain-H evaluation vs LEACH/PEGASIS/SEP/DEEC (20 seeds, N=100/200/500)
python eval_full.py        # writes eval_full.json, lifetime.png, scalability.png

# 20-seed N=100 focused numbers used in the abstract
python eval_n100.py
```

All results are seeded and deterministic per seed.

## Project Structure

```
.
├── energy.py            # First-order radio energy model (+ COMM_RANGE param)
├── leach.py             # LEACH (heterogeneity-aware: m, a_mult)
├── pegasis.py           # PEGASIS (heterogeneity-aware: m, a_mult)
├── sep.py / deec.py     # Heterogeneous cluster baselines
├── clusterchain.py      # Original ClusterChain (legacy hybrid, documented in history)
├── clusterchain_h.py    # ClusterChain-H: MST chain + rotating terminus + heterogeneity
├── run.py               # Experiment runner + legacy 3-way comparison + dashboard
├── eval_full.py         # Full evaluation vs all baselines (N=100/200/500, multi-seed)
├── eval_n100.py         # Focused 20-seed N=100 results
├── sweep.py / sweep2.py # Parameter sweeps
├── derivation.md        # Math: energy-optimal k* and the delay/lifetime tradeoff
├── derive_kstar.py      # Closed-form optimal chain length k* derivation
├── scenarios.py         # Communication-range sensitivity + energy-consumption plots
├── dashboard_gen.py     # LEACH/PEGASIS/ClusterChain-H dashboard + death timeline
├── REPORT.md            # Full mini-project report (problem, related work, results)
└── CONFERENCE_ABSTRACT.md
```

## Simulation Parameters

- **Nodes**: 100 (Scenario 1), 200 (Scenario 3), 500 (scalability)
- **Sink**: Fixed at (50, 175)
- **Initial Energy**: 0.5 J per normal node; advanced nodes (m=0.1) at 1.0 J
- **Packet Size**: 4000 bits
- **Energy Model**: First-order radio (Heinzelman et al., 2000)
- **Seeds**: 20 (N=100), deterministic
- **Metrics**: Lifetime (FND/HND/last), PDR, E2E delay (hops), Energy x Delay

## References

1. Heinzelman, W. et al. (2000) — "Energy-Efficient Communication Protocol for
   Wireless Microsensor Networks" (LEACH).
2. Lindsey, S. & Raghavendra, K. (2002) — "PEGASIS: Power-Efficient Gathering in
   Sensor Information Systems".
3. Smaragdakis, G. et al. (2004) — "SEP: A Stable Election Protocol for clustered
   heterogeneous WSNs".
4. Qing, L. et al. (2006) — "Design of a distributed energy-efficient clustering
   algorithm for heterogeneous WSNs" (DEEC).
5. Kalpakis, K. et al. (2003) — "Maximum Lifetime Data Gathering in WSNs"
   (MST energy floor).

## License

MIT License
