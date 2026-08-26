# LEACH vs PEGASIS vs ClusterChain: WSN Routing Protocol Comparison

Simulation-based performance comparison of three hierarchical routing protocols
for Wireless Sensor Networks (WSNs), including a hybrid protocol (ClusterChain)
proposed and evaluated in this project.

## Overview

This project implements and compares three routing protocols:

- **LEACH** (Low-Energy Adaptive Clustering Hierarchy) — probabilistic cluster
  head rotation. Random cluster-head election ignores residual energy and
  distance to the sink, so a far cluster head can pay a costly multipath hop
  every round (Heinzelman et al., 2000).
- **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems) — a
  greedy chain over all nodes. Energy is balanced well, but every node relays
  every round (high delay, ~100 hops) and the chain-end leader is a permanent
  hotspot (Lindsey & Raghavendra, 2002).
- **ClusterChain** — a hybrid that combines LEACH-style clustering with a
  PEGASIS-style greedy chain. Cluster heads are elected by a score that weights
  residual energy and proximity to the sink; only the cluster-head set (or, in
  dense mode, all nodes) forms the relay chain to the sink; and the chain
  terminus that performs the single expensive sink hop rotates by residual
  energy and proximity each round. This removes PEGASIS's permanent leader
  hotspot and keeps end-to-end delay low while preserving PEGASIS's short,
  energy-cheap hops.

All three protocols share a first-order radio energy model
(Heinzelman et al., 2000) so the comparison is like-for-like.

## Key Results

Network lifetime and delivery metrics, averaged over 3 seeded runs
(100 nodes, 100m x 100m field, sink at (50, 175), 0.5 J initial energy):

| Metric | LEACH | PEGASIS | ClusterChain | Notes |
|--------|-------|---------|--------------|-------|
| First node death (round) | 1 | 1 | 1 | random CH / leader can die immediately |
| 50% nodes dead (round) | 819 | 1183 | 1156 | ClusterChain ~ PEGASIS, +41% vs LEACH |
| Last node dead (round) | 839 | 1200 | 1160 | ClusterChain matches PEGASIS within noise |
| Network lifetime vs LEACH | 1.00x | 1.44x | 1.41x | ClusterChain roughly ties PEGASIS |
| Average delay (hops) | ~1 | ~100 | 5-7 (clustered) / ~100 (dense) | clustered mode fixes PEGASIS delay; dense matches it |
| Packet Delivery Ratio | high, collapses at death | periodic drops to ~0.65 | stays ~1.0 until near death | consistent delivery metric |

**Honest summary:** ClusterChain does not strictly beat PEGASIS on raw network
lifetime — PEGASIS's dense greedy chain is near-optimal for this energy model,
and the swept parameter grid (cluster-head count, energy weight, cluster-head
selection strategy, terminus rule) confirmed PEGASIS stays ahead within ~2%.
ClusterChain's contribution is on the *multi-objective* front:

- **Clustered mode (k = 5-7 cluster heads):** 5-15x lower end-to-end delay than
  PEGASIS (5-7 hops vs ~100) at the cost of ~5% lifetime (1114-1128 vs 1183).
- **Dense mode (k = N):** matches PEGASIS on lifetime (1162 vs 1183) and delay,
  but with a rotated terminus instead of a permanent leader hotspot.
- **Analytical k\* tuning:** the cluster-head count is derived from the Heinzelman
  energy model (see `derivation.md`); the model's per-round energy minimum at
  k\*=4 for N=100 anchors the delay-favoring design point, while the chain length
  k is the single knob that trades delay against lifetime. This makes ClusterChain
  a reproducible *unification* of the LEACH and PEGASIS design spaces (recovers
  LEACH at k=N non-clustered, PEGASIS at k=N dense) rather than an unprincipled
  "yet another hybrid."
- Compared with LEACH it is ~1.4x longer-lived and far more stable; PDR stays
  ~1.0 until near network death versus LEACH's collapse.

The parameter sweep that selected these defaults is in `sweep.py`; the closed-form
k\* derivation is in `derivation.md`.

## Quick Start

```bash
pip install -r requirements.txt

# Run the 3-protocol comparison (3 runs, 2000 rounds each)
python run.py --nodes 100 --rounds 2000 --runs 3

# Outputs: comparison.png, dashboard.png, results.json
```

## Project Structure

```
.
├── energy.py          # First-order radio energy model
├── leach.py           # LEACH protocol implementation
├── pegasis.py         # PEGASIS protocol implementation
├── clusterchain.py    # ClusterChain (hybrid) protocol implementation
├── run.py             # Experiment runner + 3-way comparison + dashboard
├── sweep.py           # Parameter sweep to select ClusterChain defaults
├── derive_kstar.py    # Closed-form optimal chain length k* derivation
├── derivation.md      # Math: energy-optimal k* and the delay/lifetime tradeoff
├── kstar_result.txt   # Numeric output of derive_kstar.py
├── results.json       # Raw per-run data for all three protocols
├── comparison.png     # 6-panel comparison (lifetime, energy, PDR, delay, throughput, loss)
└── dashboard.png      # Lifetime milestone bar chart
```

## Simulation Parameters

- **Nodes**: 100, randomly deployed in 100m x 100m field
- **Sink**: Fixed at (50, 175)
- **Initial Energy**: 0.5 J per node
- **Packet Size**: 4000 bits
- **Energy Model**: First-order radio (Heinzelman et al., 2000)
- **Runs**: 3 independent seeds, up to 2000 rounds each

## References

1. Heinzelman, A., Chandrakasan, & Balakrishnan (2000) — "Energy-Efficient
   Communication Protocol for Wireless Microsensor Networks" (LEACH).
2. Lindsey, S. & Raghavendra, K. (2002) — "PEGASIS: Power-Efficient Gathering
   in Sensor Information Systems".
3. Handy, M. J., Haase, M. & Timmermann, D. (2002) — "Low Energy Adaptive
   Clustering Hierarchy with Deterministic Cluster-Head Selection" (LEACH-D /
   energy-aware CH election foundations).
4. Qing, L., Zhu, Q. & Wang, M. (2006) — "Design of a distributed energy-efficient
   clustering algorithm for heterogeneous WSNs" (DEEC; residual-energy-weighted
   cluster-head selection).
5. Farooq, M. O. et al. (2010) — "MR-LEACH: Multi-hop Routing with LEACH" (multi-hop
   cluster-head to sink relay).
6. Lindsey, S., Raghavendra, K. & Sivalingam, K. M. (2002) — "Data Gathering
   in Sensor Networks using the PEGASIS Chain-Based Protocol"
   (H-PEGASIS / parallel chains for delay reduction).

## License

MIT License
