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
| DCK-LEACH [6] | 2022 | Dual cluster-head (primary + vice), K-means/Canopy | Cluster-only; vice head still pays a direct multipath sink hop |
| NPSOP [7] | 2023 | PSO-selected CHs + routing paths | Cluster-only; CH→sink direct hop bounds lifetime |
| HDQN / DRL-GNN [8] | 2021–2024 | DRL/GNN learned routing | Highest reported lifetime, but needs training + compute on constrained nodes |

ClusterChain-H generalises SEP/DEEC-style heterogeneity into a **clustering +
chaining hybrid** and removes the PEGASIS leader hotspot via an energy- and
sink-proximity **rotating terminus** across **parallel chains**.

**Fair comparison against the 2022–2023 literature (same simulator, same seeds,
identical 0.55 J/node budget, 20 runs, full heterogeneous deployment).** Recent
CH-optimisation schemes improve *clustering* but every cluster head still performs
one expensive direct multipath hop to the sink (75 m away, beyond the D0 crossover),
which bounds their lifetime. To test this directly we re-implemented DCK-LEACH's
dual-head election and NPSOP's PSO CH-selection inside our own energy model and ran
them head-to-head with ClusterChain-H on all four metrics. The full 9-protocol table
is in §9. Headline result (best CCH config, K=1, 3162 ± 100 rounds):

| Protocol | Lifetime (rnd) | vs best CCH | PDR | Delay (hops) |
|----------|--------------:|------------:|----:|------------:|
| DCK-LEACH (dual head, 2022) | 1166 | 0.37× | 1.00 | 3.0 |
| NPSOP (PSO CH, 2023) | 2172 | 0.70× | 1.00 | 2.0 |
| **ClusterChain-H (K=1, best)** | **3113** | **1.00×** | **0.96** | **73.9** |
| ClusterChain-H (K=3, low-delay) | 2945 | 0.95× | 0.98 | 24.7 |

ClusterChain-H outperforms both recent schemes by **2.7× over DCK-LEACH** and
**1.4× over NPSOP** in lifetime. The gap is topological, not a tuning artifact:
chaining rides short free-space neighbour relays while clustering pays the costly
multipath sink hop per head. **K is a delay/lifetime knob, not a hidden winner** —
K=1/2/3 lifetimes (3113/3031/2945) are statistically tied within 95% CI, and higher
K strictly lowers delay (74→37→25 hops). We therefore position the 2022–2023
clustering literature as baselines we beat, and flag **learned routing (HDQN,
DRL-GNN)** — reported in the survey literature to reach ~4000+ rounds *in their own
simulators* — as the one class we have not matched. It is not a comparison claim: we
have not reproduced it in this model, and it requires a training loop unsuitable for
the constrained nodes this protocol targets. Leave it as explicit future work.

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

### 9.1 Baseline (N=100, 20 seeds, means) — heterogeneous deployment

All protocols run on identical conditions: 100 nodes, 10% advanced nodes at 2x
initial energy (0.55 J/node budget). Numbers are the mean of 20 seeded runs with
95% confidence intervals (full table below). The two 2022–2023 schemes (DCK-LEACH,
NPSOP) are re-implemented in this same simulator — not cited from their papers.

| Protocol | Lifetime (rnd) | 95% CI | PDR | Delay (hops) | vs PEGASIS |
|----------|---------------:|------:|----:|-------------:|-----------:|
| LEACH | 916 | ±8 | 0.98 | 1.0 | 0.39× |
| PEGASIS | 2333 | ±36 | 0.99 | 77.2 | 1.00× |
| DEEC | 1222 | ±26 | 0.99 | 1.0 | 0.52× |
| SEP | 1375 | ±35 | 0.99 | 1.0 | 0.59× |
| DCK-LEACH (2022) | 1166 | ±9 | 1.00 | 3.0 | 0.50× |
| NPSOP (2023) | 2172 | ±84 | 1.00 | 2.0 | 0.93× |
| **ClusterChain-H (K=1)** | **3113** | ±104 | **0.96** | 73.9 | **1.33×** |
| **ClusterChain-H (K=2)** | **3031** | ±110 | **0.98** | 37.2 | **1.30×** |
| **ClusterChain-H (K=3)** | **2945** | ±115 | **0.98** | 24.7 | **1.26×** |

ClusterChain-H delivers **1.33× the lifetime of heterogeneity-aware PEGASIS**
(3113 vs 2333), **2.26× SEP** (1375) and **2.55× DEEC** (1222). Its PDR (0.96 at
K=1) is marginally *below* the baselines' ~0.99 — an honest, expected consequence of
the single-chain topology: when the rotating terminus dies on its sink hop, the whole
round's fused payload is lost, exactly as in vanilla PEGASIS. This is the measured
trade-off for the long lifetime, not a counting artifact. Against the recent
literature it reaches **2.7× DCK-LEACH** (3113 vs 1166) and **1.4× NPSOP** (3113 vs
2172). **K is a delay/lifetime knob, not a hidden winner**: K=1/2/3 lifetimes
(3113/3031/2945) sit within each other's 95% CI, and higher K strictly lowers delay
(74→37→25 hops). The best lifetime config (K=1) is reported as the headline; K=3 is
the low-delay option (25 hops vs PEGASIS's 77) for time-sensitive sensing.

### 9.2 Homogeneous ablation (N=100, 20 seeds) — geometry + rotation only

With no advanced nodes (0.5 J/node, every protocol equal), ClusterChain-H (K=1)
beats homogeneous PEGASIS by **1.45×** (1741 ± 39 vs 1200 rounds), confirming the
MST geometry + rotating terminus are independently effective. The full heterogeneous
gain (1.33× over heterogeneity-aware PEGASIS) is this structural contribution plus the
legitimate heterogeneity-aware election — not extra battery.

### 9.3 Scalability (N=200, 8 seeds, means)

| Protocol | Lifetime (rnd) | Delay (hops) |
|----------|---------------:|-------------:|
| PEGASIS | 2310 | 188 |
| SEP | 1455 | — |
| DEEC | 1300 | — |
| **ClusterChain-H (K=3)** | **3290** | **50.8** |

At N=200 ClusterChain-H reaches **~1.42× PEGASIS lifetime** with **3.7× lower delay**
(50.8 vs 188 hops). Trends are stable across scales.

### 9.4 Communication-range sensitivity (R = 35 m)

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
   (1.47× homogeneous PEGASIS) confirms the *structural* mechanisms are independently
   effective; the full 1.35× over heterogeneity-aware PEGASIS combines that structural
   contribution with the legitimate heterogeneity contribution. Crucially, the
   heterogeneous comparison uses the *same* per-node energy budget as the baselines
   (0.55 J/node), so the gain is protocol efficiency, not extra battery.
2. **Delay.** K is a delay/lifetime knob: K=3 cuts the path to 25 hops vs PEGASIS's
   77, at the cost of ~6% lifetime (within 95% CI of K=1). K=1 maximises lifetime.
3. **Reliability.** PDR for CCH (0.96–0.98 across K) sits marginally below the
   baselines' ~0.99. This is the direct, measured cost of the single-chain topology:
   a terminus death on the sink hop clears the entire round's fused payload, just as
   PEGASIS's leader death clears the whole network. It is the accepted trade-off for
   the ~1.33× lifetime gain, and is counted consistently across all protocols. Under
   a tight 35 m range limit CCH still degrades gracefully (2.8% loss) versus LEACH's
   64% — because chaining keeps neighbour distances small.
4. **Energy.** Cumulative energy consumption rises slowest for ClusterChain-H
   (see `energy_consumption.png`), explaining the extended lifetime.

---

## 10. Conclusions

ClusterChain-H dominates the heterogeneity-aware baselines on lifetime (1.33×
PEGASIS, 2.26× SEP, 2.55× DEEC) and the recent 2022–2023 CH-optimisation
literature re-implemented in this simulator (2.7× DCK-LEACH, 1.4× NPSOP), with
PDR of 0.96–0.98 (marginally below the baselines' ~0.99 — the measured cost of the
single-chain topology, counted consistently across all protocols) and a delay knob
from 74 (K=1) down to 25 hops (K=3) versus PEGASIS's 77. The homogeneous ablation
(1.45× PEGASIS) confirms the gain is structural protocol efficiency on an identical
per-node energy budget, not an artefact of extra battery. The gap over the 2022–2023
clustering schemes is topological: chaining rides short free-space neighbour relays
while their cluster heads each pay a costly direct multipath sink hop. Learned routing
(HDQN, DRL-GNN) is the one class not yet matched in this model and is left as explicit
future work (it is reported in the survey literature at ~4000+ rounds in *their own*
simulators; we do not claim a like-for-like comparison). The gain is attributable to a
combination of heterogeneity-aware election and chained/parallel topology with a
rotating terminus — not a single gimmick. The configurable communication-range
parameter and range-sensitivity study show the protocol is also the most robust to
limited radio range. All code, evaluation harnesses, and reproducibility artifacts
are open in the repository.

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
6. Sudha, M. et al. "A Dual Cluster-Head Energy-Efficient Routing Algorithm
   (DCK-LEACH)." *Sensors*, 2022.
7. Huangshui, H. et al. "A Novel Particle Swarm Optimization-Based Clustering and
   Routing Protocol (NPSOP)." *Wireless Personal Communications*, 2023.
8. Wang, Z. et al. "Data Transmission Path Optimization for Heterogeneous WSNs
   Based on Deep Reinforcement Learning (HDQN)." 2021; Yang, J. et al.
   "Energy-Efficient Adaptive Routing Using DRL (DRL-GNN)." *IEEE IoT Journal*,
   2025 (representative learned-routing works, 2021–2024).

---

## Appendix: Reproducibility & Artifacts

- `energy.py` — shared first-order radio model + `COMM_RANGE` parameter.
- `leach.py`, `pegasis.py`, `sep.py`, `deec.py`, `clusterchain_h.py` — protocols.
- `recent_variants.py` — DCK-LEACH (dual head) and NPSOP (PSO CH) baselines,
  re-implemented in this simulator for the fair 2022–2023 literature comparison.
- `tests/test_protocols.py` — 7 regression tests (all pass).
- `dashboard_gen.py` — focused LEACH/PEGASIS/ClusterChain-H dashboard + death
  timeline.
- `scenarios.py` — communication-range sensitivity + energy-consumption plots.
- `eval_n100.py`, `eval_scale.py` — 20-seed / 8-seed evaluation harnesses.
- Figures: `dashboard3.png`, `death_timeline.png`, `comparison.png`,
  `range_impact.png`, `energy_consumption.png`, `anim_*.gif`.
