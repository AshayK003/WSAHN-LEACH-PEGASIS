# ClusterChain-H: A Heterogeneity-Aware Multichain Routing Protocol for WSNs

## Abstract

Cluster-based (LEACH) and chain-based (PEGASIS) routing remain the two canonical
data-gathering strategies for wireless sensor networks, but each carries a structural
weakness: LEACH elects cluster heads at random and wastes energy on distant or
multipath relay hops, while PEGASIS forms a single chain that forces every
node to relay, yielding ~77-hop end-to-end delay and round-robin leadership
that still assigns the costly multipath sink hop to far or energy-poor nodes.

We propose **ClusterChain-H**, a synthesis that addresses both weaknesses through
four mechanisms:

1. **Near-optimal chain geometry** — a Prim's MST-based chain construction
   (minimum-total-length aggregation in the MLDA spirit of Kalpakis et al.;
   MST-traversal chains after Meghanathan) replaces greedy
   nearest-neighbour chaining, eliminating long links.
2. **Energy + sink-proximity rotating terminus** — the sink hop is performed by the
   node maximising residual energy and proximity to the base station, rotated every
   round. This removes PEGASIS's far/multipath leader bottleneck.
3. **Heterogeneity-aware election** — cluster heads / chain relays are elected by a
   weighted score of residual energy and node type (SEP/DEEC style), so advanced
   nodes bear the expensive relay and aggregation load.
4. **Multichain parallelism** — a tunable number K of parallel chains
   trades delay against lifetime, with K=1 as the lifetime-optimal sweet spot.

All protocols are evaluated under a single first-order radio model with
**identical deployment conditions** (100 nodes, 10% advanced nodes at 2x initial
energy, 20 seeded runs): lifetime is normalised by per-node energy budget so gains
are not an artefact of extra battery. In this fair comparison the best ClusterChain-H
configuration (K=1, 3038 ± 127 rounds) achieves **1.33x the lifetime of
heterogeneity-aware PEGASIS (2291 ± 41)**, **1.99x SEP (1528 ± 86)** and
**2.57x DEEC (1184 ± 21)**, with **PDR = 0.96** (PEGASIS 0.99; the small gap is a
single-chain terminus death clearing the round, an accepted cost of the long
lifetime) and end-to-end delay of **25-75 hops versus PEGASIS's 77**. K is a
delay/lifetime knob, not a hidden winner: K=1-3 are within each other's 95% CI on
lifetime (3038/2931/2819), and higher K strictly lowers delay (75/37/25 hops).
**Where the gain comes from.** An H-PEGASIS baseline (MST-refined geometry + rotating
leader, run homogeneously) already reaches **3084 ± 120 rounds (1.35x PEGASIS)**,
showing the structural mechanism accounts for nearly the entire lifetime jump;
ClusterChain-H matches this geometry gain while adding the heterogeneity-aware election,
which does not extend raw lifetime further (the rotating terminus already load-balances)
but guarantees fairness — normal nodes survive 2.56x longer than advanced nodes (Section
9.2) — at zero lifetime cost, and still beats the heterogeneity-only baselines SEP/DEEC
by 2.0-2.6x.
To test against the recent literature we re-implemented two 2022-2023 CH-optimisation
schemes (DCK-LEACH dual cluster-head, NPSOP PSO cluster-head selection) inside the
same model: both remain clustering protocols whose heads pay a direct multipath sink
hop, and ClusterChain-H outperforms them by **2.6x DCK-LEACH (3038 vs 1171)** and
**1.5x NPSOP (3038 vs 2092)** in lifetime. A homogeneous ablation (geometry +
rotation only, no heterogeneity) yields **1.45x the lifetime of homogeneous PEGASIS
(1742 ± 38 vs 1200 rounds)**, confirming the structural mechanisms are independently
effective; the full heterogeneous gain combines that structural contribution with the
legitimate heterogeneity-aware election. Learned routing (HDQN, MADII) is reported
in the literature to reach longer lifetimes in their own simulators but needs a
training loop unsuitable for the constrained nodes this
protocol targets, and is left as explicit future work — it has not been reproduced in
our model and is not a comparison claim. Ablation study (Section 12) shows two
popular next-step mechanisms (energy-gradient relay, selective dual-terminus)
do not beat the baseline, while a rotating relay-sink tier reaches **~2.0x
PEGASIS** (1.50x the ClusterChain-H K=1 baseline) with PDR 1.00 under the same
20-seed benchmark. All code, evaluation harness, and reproducibility artifacts
are open.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
heterogeneity, energy efficiency, network lifetime.
