# ClusterChain-H: A Heterogeneity-Aware Multichain Routing Protocol for WSNs

## Abstract

Cluster-based (LEACH) and chain-based (PEGASIS) routing remain the two canonical
data-gathering strategies for wireless sensor networks, but each carries a structural
weakness: LEACH elects cluster heads at random and wastes energy on distant or
multipath relay hops, while PEGASIS forms a single chain that forces every
node to relay, yielding ~90-hop end-to-end delay and a permanent leader hotspot.

We propose **ClusterChain-H**, a synthesis that addresses both weaknesses through
four mechanisms:

1. **Near-optimal chain geometry** — a Prim's MST-based chain construction
   (theoretically near the per-round energy floor of Kalpakis et al.) replaces greedy
   nearest-neighbour chaining, eliminating long links.
2. **Energy + sink-proximity rotating terminus** — the sink hop is performed by the
   node maximising residual energy and proximity to the base station, rotated every
   round. This removes PEGASIS's far/multipath leader bottleneck.
3. **Heterogeneity-aware election** — cluster heads / chain relays are elected by a
   weighted score of residual energy and node type (SEP/DEEC style), so advanced
   nodes bear the expensive relay and aggregation load.
4. **Adaptive multichain parallelism** — a tunable number K of parallel chains
   trades delay against lifetime, with K=1-3 as the sweet spot.

All protocols are evaluated under a single first-order radio model with
**identical deployment conditions** (100 nodes, 10% advanced nodes at 2x initial
energy, 20 seeded runs): lifetime is normalised by per-node energy budget so gains
are not an artefact of extra battery. In this fair comparison the best ClusterChain-H
configuration (K=1, 3162 ± 100 rounds) achieves **1.35x the lifetime of
heterogeneity-aware PEGASIS (2347 ± 35)**, **2.39x SEP (1326 ± 19)** and
**2.60x DEEC (1215 ± 25)**, with **PDR = 1.00** versus ~0.98-0.99 for the
baselines and end-to-end delay of **25-75 hops versus PEGASIS's 77-93**. K is a
delay/lifetime knob, not a hidden winner: K=1-3 are within each other's 95% CI on
lifetime (3162/3105/2962), and higher K strictly lowers delay (74/37/25 hops).
To test against the recent literature we re-implemented two 2022-2023 CH-optimisation
schemes (DCK-LEACH dual cluster-head, NPSOP PSO cluster-head selection) inside the
same model: both remain clustering protocols whose heads pay a direct multipath sink
hop, and ClusterChain-H outperforms them by **2.7x DCK-LEACH (3162 vs 1173)** and
**1.5x NPSOP (3162 vs 2091)** in lifetime. A homogeneous ablation (geometry +
rotation only, no heterogeneity) yields **1.47x the lifetime of homogeneous PEGASIS
(1764 vs 1200 rounds)**, confirming the structural mechanisms are independently
effective; the full heterogeneous gain combines that structural contribution with the
legitimate heterogeneity-aware election. Learned routing (HDQN, DRL-GNN) is reported
in the survey literature to reach longer lifetimes (~4000+ rounds in their own
simulators) but needs a training loop unsuitable for the constrained nodes this
protocol targets, and is left as explicit future work — it has not been reproduced in
our model and is not a comparison claim. All code, evaluation harness, and
reproducibility artifacts are open.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
heterogeneity, energy efficiency, network lifetime.
