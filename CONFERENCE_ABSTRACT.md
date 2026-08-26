# ClusterChain: A Hybrid Clustering-Chaining Protocol for Energy-Efficient Wireless Sensor Networks

## Abstract

Cluster-based (LEACH) and chain-based (PEGASIS) routing remain the two canonical
data-gathering strategies for wireless sensor networks, but each carries a structural
weakness: LEACH elects cluster heads at random and wastes energy on distant or
multipath relay hops, while PEGASIS forms a single 100-node chain that forces every
node to relay and yields ~100-hop end-to-end delay with a permanent leader hotspot.

We propose **ClusterChain**, a synthesis that keeps the best of both. Cluster heads are
elected by a weighted score of residual energy and distance to the sink, eliminating
LEACH's random-head waste. Only the elected heads form a short greedy chain to the base
station, so non-head nodes relay at most one hop (fixing PEGASIS's ~100-hop delay).
The chain terminus that performs the single expensive sink-hop rotates every round by
weighted residual energy and sink proximity, removing PEGASIS's permanent leader
bottleneck.

Across 100-node, 100x100 m simulations (Heinzelman first-order radio model, 0.5 J
initial energy, sink at (50,175)), ClusterChain is evaluated on a uniform
packet-delivery metric (packets reaching the sink / packets generated) against both
baselines. The cluster-head count is derived analytically from the energy model
(see derivation): the per-round energy minimum lies at k*=4 for N=100, and the
chain length k is the single design knob trading delay against lifetime. Two
operating regimes emerge — a *clustered* regime (k=5-7) that cuts end-to-end delay
from ~100 hops to 5-7 (15x lower than PEGASIS) at a ~5% lifetime cost, and a *dense*
regime (k=N) that matches PEGASIS on lifetime (1162 vs 1183 rounds) with a rotated
terminus instead of a permanent leader hotspot. Against LEACH, ClusterChain is ~1.4x
longer-lived with stable packet delivery. ClusterChain thus unifies the LEACH and
PEGASIS design spaces under one analytically-tuned parameter, rather than proposing
an ad-hoc hybrid. All code, figures, and the three-way comparison dashboard are open
and reproducible.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
energy efficiency, network lifetime.
