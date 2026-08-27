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
are not an artefact of extra battery. In this fair comparison ClusterChain-H achieves
**1.33x the lifetime of heterogeneity-aware PEGASIS (3111 vs 2335 rounds)**,
**2.24x SEP (1391)** and **2.57x DEEC (1213)**, with **PDR = 1.00** versus
~0.98-0.99 for the baselines and end-to-end delay of **25-75 hops versus PEGASIS's
77-93**. A homogeneous ablation (geometry + rotation only, no heterogeneity) still
yields **1.41x the lifetime of homogeneous PEGASIS (1696 vs 1200)**, confirming the
structural mechanisms are independently effective; the full heterogeneous gain of
1.33x over heterogeneous PEGASIS combines that structural contribution with the
legitimate heterogeneity-aware election. The single parameter K explicitly trades
delay against lifetime, unifying the LEACH and PEGASIS design spaces. All code,
evaluation harness, and reproducibility artifacts are open.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
heterogeneity, energy efficiency, network lifetime.
