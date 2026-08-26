# ClusterChain-H: A Heterogeneity-Aware Multichain Routing Protocol for WSNs

## Abstract

Cluster-based (LEACH) and chain-based (PEGASIS) routing remain the two canonical
data-gathering strategies for wireless sensor networks, but each carries a structural
weakness: LEACH elects cluster heads at random and wastes energy on distant or
multipath relay hops, while PEGASIS forms a single chain that forces every
node to relay, yielding ~100-hop end-to-end delay and a permanent leader hotspot.

We propose **ClusterChain-H**, a synthesis that addresses both weaknesses through
four mechanisms:

1. **Near-optimal chain geometry** — a Prim's MST-based chain construction
   (theoretically near the per-round energy floor) replaces greedy nearest-neighbour
   chaining, eliminating long links.
2. **Energy + sink-proximity rotating terminus** — the sink-hop is performed by the
   node maximising residual energy and proximity to the base station, rotated every
   round. This removes PEGASIS's far/multipath leader bottleneck.
3. **Heterogeneity-aware election** — cluster heads / chain relays are elected by a
   weighted score of residual energy and node type (SEP/DEEC style), so advanced
   nodes bear the expensive relay and aggregation load.
4. **Adaptive multichain parallelism** — a tunable number K of parallel chains
   trades delay against lifetime, with K=2-3 as the sweet spot.

In heterogeneous deployments (10% advanced nodes, 2× initial energy), the protocol
achieves **2.4–2.8× the network lifetime of vanilla PEGASIS** (N=100: 2917 vs 1200
rounds; N=200: 3326 vs 1200 rounds) with **PDR = 1.00**, **end-to-end delay 25–51
hops vs PEGASIS's 92–190**, and **energy×delay 4.5× lower**. Against LEACH the
improvement is 3.5–3.9×; against heterogeneity-aware baselines (SEP, DEEC) it is
2.2–2.6×. A homogeneous ablation (geometry + rotation only, no heterogeneity)
still yields **1.48× PEGASIS** lifetime, confirming the mechanisms are independently
effective. The single parameter K explicitly trades delay against lifetime, unifying
the LEACH and PEGASIS design spaces. All code, evaluation harness, and
reproducibility artifacts are open.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
heterogeneity, energy efficiency, network lifetime.