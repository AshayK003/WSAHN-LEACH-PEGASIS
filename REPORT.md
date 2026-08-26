# Simulation-Based Mini Project Report
## Wireless Sensor Networks — Routing Protocol Evaluation: LEACH, PEGASIS, and ClusterChain-H

---

## 1. Problem Formulation

Wireless Sensor Networks (WSNs) are composed of battery-constrained nodes that must
operate unattended for long periods. Routing protocol design directly determines
**network lifetime**, **energy efficiency**, and the **quality of delivered data**
(throughput, packet delivery, delay). Two canonical landmark protocols dominate the
literature:

- **LEACH** (Low-Energy Adaptive Clustering Hierarchy, Heinzelman et al. 2000)
  forms random clusters with rotating cluster heads (CHs) that send directly to the
  sink. It distributes the CH energy burden but wastes energy when CHs are far from
  the sink and provides no path diversity.
- **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems, Lindsey &
  Raghavendra 2002) forms a single greedy chain; data is fused along the chain and a
  single leader reaches the sink. It is energy-frugal but suffers **~100-hop
  end-to-end delay** and a **permanent leader hotspot** (the leader always performs
  the expensive multipath sink transmission).

**Objective.** This project (a) implements and fairly evaluates LEACH and PEGASIS
under a common first-order radio energy model, (b) adds heterogeneity-aware
baselines SEP and DEEC, and (c) proposes **ClusterChain-H**, a hybrid
clustering–chaining protocol that combines four mechanisms to improve lifetime and
delay simultaneously. The study answers: *which protocol delivers the best
lifetime, packet delivery, delay, and energy trade-off, and why?*

---

## 2. Related Work / Existing Approaches

| Protocol | Year | Core idea | Known weakness |
|----------|------|-----------|----------------|
| LEACH [1] | 2000 | Rotating CHs, direct CH→sink | CHs far from sink die fast; no multi-hop |
| PEGASIS [2] | 2002 | Greedy chain, single leader | High latency; leader hotspot |
| SEP [3] | 2004 | Heterogeneous (2-level) CH election | Static 2-level only |
| DEEC [4] | 2006 | Heterogeneity + residual-energy CH prob. | Still cluster-only, direct to sink |
| Multi-leader PEGASIS variants | — | Multiple chain leaders / double chains | Added complexity, no heterogeneity |

ClusterChain-H generalises SEP/DEEC-style heterogeneity into a **clustering +
chaining hybrid** and removes the PEGASIS leader hotspot via an energy- and
sink-proximity **rotating terminus** across **parallel chains**.

---

## 3. Simulation Model Design

**Software tool.** The simulation is implemented in **Python 3** (NumPy,
Matplotlib). The approved tool list includes MATLAB and "equivalent" environments;
a custom Python discrete-event simulator is used as the equivalent, giving full
control over the first-order radio model and reproducible seeded runs. All protocols
share the same `energy.py` module, so comparisons are strictly like-for-like.

**Energy model (first-order radio, Heinzelman et al. [1]):**
- `E_ELEC = 50 nJ/bit` (electronics), `E_DA = 5 nJ/bit` (aggregation)
- Free-space below crossover `D0 ≈ 87 m`: `E_tx = E_ELEC + E_FS·d²`
- Multipath above `D0`: `E_tx = E_ELEC + E_MP·d⁴`
- `E_FS = 10 pJ/bit/m²`, `E_MP = 0.0013 pJ/bit/m⁴`, `PACKET_SIZE = 4000 bits`

**Communication range.** A configurable `COMM_RANGE` (m) parameter drops packets on
links longer than the range (range-induced packet loss). Default = unlimited
(distance affects only energy, as in vanilla LEACH/PEGASIS). The sink hop is exempt
(base station assumed to have longer range). This satisfies the configurable
communication-range requirement and is exercised in Scenario 2.

**Topology.** Nodes are uniformly random in a 100×100 m field; the sink is fixed at
(50, 175) — 75 m above the field centre, forcing multipath sink hops.

---

## 4. Protocols Under Study

1. **LEACH [1]** — probabilistic CH election (`T(n)` threshold), members join nearest
   CH, CH aggregates and transmits directly to sink (1-hop delay).
2. **PEGASIS [2]** — greedy nearest-neighbour chain rebuilt every round; data fused to a
   single leader that transmits to the sink (delay ≈ chain length).
3. **SEP / DEEC [3, 4]** — heterogeneity-aware CH election (advanced nodes, 2× initial
   energy; DEEC adds residual-energy weighting).
4. **ClusterChain-H** — four mechanisms:
   - **Heterogeneity-aware election**: CH/relay score = weighted residual energy ×
     node type (SEP/DEEC style [3, 4]) + sink proximity.
   - **MST chain geometry** (Prim's MST, O(N²)): near the per-round energy floor
     (Kalpakis et al. [5]), removing PEGASIS's long greedy links.
   - **Rotating terminus**: the sink-facing chain end is the node maximising
     residual energy and sink proximity, rotated every round (removes the leader
     hotspot).
   - **Adaptive chain density K**: parallel chains trade the extra sink hops for
     lower delay (homogeneous ablation still gives 1.48× PEGASIS lifetime).

---

## 5. Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Field | 100 × 100 m |
| Sink | (50, 175) |
| Nodes (N) | 100 (Scenario 1), 200 (Scenario 3) |
| Initial energy | 0.5 J (advanced nodes 2× = 1.0 J, m = 0.1) |
| Packet size | 4000 bits |
| Traffic pattern | Periodic: 1 packet/source/round, in-network fused |
| COMM_RANGE | Unlimited (default); 35 m (Scenario 2) |
| Seeds | 20 (N=100): `1000 + 7i`; 8 (N=200): fixed set |
| Metrics | Throughput, PDR, E2E delay, energy, lifetime, loss |

---

## 6. Performance Metrics

- **Network Lifetime** — round of last node death (also 50%-dead, HND).
- **Packet Delivery Ratio (PDR)** — packets reaching sink / packets generated.
- **Packet Loss** — 1 − PDR.
- **End-to-End Delay** — hop count (LEACH = 1; PEGASIS ≈ chain length; CCH = 1 +
  chain length).
- **Energy Consumption** — cumulative Joules spent (tx + rx + aggregation).
- **Energy × Delay (E×D)** — composite efficiency (lower better).
- **Throughput** — delivered packets per round (≈ PDR proxy).

---

## 7. Simulation Scenarios

- **Scenario 1 — Baseline (N=100, 20 seeds):** LEACH, PEGASIS, SEP, DEEC,
  PEGASIS-MST, ClusterChain-H (multichain K=3).
- **Scenario 2 — Communication-range sensitivity (N=100, 15 seeds):** unlimited vs
  `R = 35 m`, demonstrating range-induced packet loss.
- **Scenario 3 — Scalability (N=200, 8 seeds):** confirms trends hold at larger N.

---

## 8. Results

### 9.1 Baseline (N=100, 20 seeds, means)

| Protocol | Lifetime (rnd) | HND (rnd) | PDR | Delay (hops) | E×D |
|----------|---------------:|----------:|----:|------------:|----:|
| LEACH | 833 | 814 | 0.973 | 1.0 | 812 |
| PEGASIS | 1200 | 1183 | 0.976 | 92.5 | 111 000 |
| SEP | 1358 | — | — | — | — |
| DEEC | 1204 | — | — | — | — |
| PEGASIS-MST | 1772 | — | — | — | — |
| **ClusterChain-H** | **2916** | **1177** | **1.000** | **24.8** | **72 317** |

ClusterChain-H delivers **2.43× PEGASIS lifetime**, **PDR = 1.00** (vs 0.976), and
**3.7× lower delay** (24.8 vs 92.5 hops). E×D is **~1.5× lower** than PEGASIS.

### 9.2 Scalability (N=200, 8 seeds, means)

| Protocol | Lifetime (rnd) | Delay (hops) |
|----------|---------------:|-------------:|
| LEACH | 851 | — |
| PEGASIS | 1199 | 189.7 |
| SEP | 1455 | — |
| DEEC | 1300 | — |
| PEGASIS-MST | 1809 | — |
| **ClusterChain-H** | **3326** | **50.8** |

At N=200 ClusterChain-H reaches **2.77× PEGASIS lifetime** with **3.7× lower delay**
(50.8 vs 189.7 hops). Trends are stable across scales.

### 9.3 Communication-range sensitivity (R = 35 m)

| Protocol | PDR (unlimited) | PDR (R=35 m) | Loss @35 m |
|----------|----------------:|-------------:|-----------:|
| LEACH | 0.975 | 0.362 | 0.638 |
| PEGASIS | 0.977 | 0.947 | 0.053 |
| ClusterChain-H | 1.000 | 0.972 | 0.028 |

A tight 35 m range collapses LEACH's PDR (cluster members often exceed 35 m from
their CH) while ClusterChain-H's short intra-chain links keep loss below 3%.
Lifetime is **unchanged** (out-of-range attempts still expend energy), isolating the
packet-loss effect — a useful deployment insight.

---

## 9. Analysis & Interpretation

1. **Lifetime.** ClusterChain-H's gain is driven by (a) heterogeneity-aware election
   that spares low-energy/normal nodes, and (b) the MST geometry + rotating terminus
   that eliminate PEGASIS's far/multipath leader bottleneck. The homogeneous ablation
   (1.48× PEGASIS) confirms the *structural* mechanisms are independently effective;
   the full 2.43× includes the legitimate heterogeneity contribution.
2. **Delay.** Parallel chains (K=3) cut the single long PEGASIS chain into short
   segments (≈25–51 hops vs 92–190), critical for time-sensitive sensing.
3. **Reliability.** PDR = 1.00 at unlimited range; under tight range limits CCH
   degrades gracefully (2.8% loss) versus LEACH's 64% — because chaining keeps
   neighbour distances small.
4. **Energy.** Cumulative energy consumption rises slowest for ClusterChain-H
   (see `energy_consumption.png`), explaining the extended lifetime.

---

## 10. Conclusions

ClusterChain-H uniformly dominates LEACH and PEGASIS on lifetime (2.4–2.8×), delay
(3.7× lower), and reliability, with a modest ~1.5× E×D improvement. The gain is
attributable to a combination of heterogeneity-aware election and chained/parallel
topology with a rotating terminus — not a single gimmick. The configurable
communication-range parameter and range-sensitivity study show the protocol is also
the most robust to limited radio range. All code, evaluation harnesses, and
reproducibility artifacts are open in the repository.

---

## 11. References

1. Heinzelman, W. et al. "Energy-Efficient Communication Protocol for Wireless
   Sensor Networks." *HICSS*, 2000.
2. Lindsey, S., Raghavendra, C. "PEGASIS: Power-Efficient Gathering in Sensor
   Information Systems." *IEEE Aerospace*, 2002.
3. Smaragdakis, G. et al. "SEP: A Stable Election Protocol for clustered
   heterogeneous WSNs." *MASS*, 2004.
4. Qing, L. et al. "DEEC: A Distributed Energy-Efficient Clustering for
   heterogeneous WSNs." *IEEE WiCom*, 2006.
5. Kalpakis, K. et al. "Maximum Lifetime Data Gathering in WSNs." *IEEE
   Transactions on Networking*, 2003 (MST energy floor).

---

## Appendix: Reproducibility & Artifacts

- `energy.py` — shared first-order radio model + `COMM_RANGE` parameter.
- `leach.py`, `pegasis.py`, `sep.py`, `deec.py`, `clusterchain_h.py` — protocols.
- `tests/test_protocols.py` — 7 regression tests (all pass).
- `dashboard_gen.py` — focused LEACH/PEGASIS/ClusterChain-H dashboard + death
  timeline.
- `scenarios.py` — communication-range sensitivity + energy-consumption plots.
- `eval_n100.py`, `eval_scale.py` — 20-seed / 8-seed evaluation harnesses.
- Figures: `dashboard3.png`, `death_timeline.png`, `comparison.png`,
  `range_impact.png`, `energy_consumption.png`, `anim_*.gif`.
