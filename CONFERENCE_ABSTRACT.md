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
baselines. Results: network lifetime (50% node death) of **1156 rounds vs PEGASIS 1183
and LEACH 819** — matching PEGASIS while delivering **~15x lower average delay**
(5-7 hops vs ~100) and removing the leader hotspot. The design is parameterised
(cluster-head count, energy weight, selection mode, terminus rule) and swept to select
defaults. All code, figures, and the three-way comparison dashboard are open and
reproducible.

**Keywords:** wireless sensor networks, LEACH, PEGASIS, clustering, chain routing,
energy efficiency, network lifetime.
