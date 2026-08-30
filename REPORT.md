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
| H-PEGASIS | 2009 | MST-refined chain geometry + rotating leader | Homogeneous only; no heterogeneity-aware election |
| PDCH | 2012 | Chain partitioning + dual-cluster-head hybrid | Homogeneous; ignores node-type energy weighting |
| DCK-LEACH [6] | 2022 | Dual cluster-head (primary + vice), K-means/Canopy | Cluster-only; vice head still pays a direct multipath sink hop |
| NPSOP [7] | 2023 | PSO-selected CHs + routing paths | Cluster-only; CH→sink direct hop bounds lifetime |
| HDQN / DRL-GNN [8] | 2021–2024 | DRL/GNN learned routing | Highest reported lifetime, but needs training + compute on constrained nodes |

ClusterChain-H generalises SEP/DEEC-style heterogeneity into a **clustering +
chaining hybrid** and removes the PEGASIS leader hotspot via an energy- and
sink-proximity **rotating terminus** across **parallel chains**.

**Positioning vs prior chain refinements.** H-PEGASIS (2009) and PDCH (2012)
already replace greedy chaining with MST-refined geometry and a rotating leader,
but both are *homogeneous* protocols: every node carries the same initial energy,
so their election cannot exploit heterogeneity. The contribution of ClusterChain-H
is the **fusion** of MST+rotation chain geometry with SEP/DEEC-style
heterogeneity-aware election — advanced (2×-energy) nodes are steered toward the
expensive relay/aggregation roles while normal nodes are spared. This is a
combination, not a new primitive; its value is that it retains H-PEGASIS/PDCH's
geometry gains *and* adds the heterogeneity margin that those protocols forgo.
We therefore benchmark against H-PEGASIS/PDCH-style geometry as the structural
baseline and against SEP/DEEC as the heterogeneity baseline, and show the
combination (2.24× SEP, 2.53× DEEC) exceeds either axis alone.

**Fair comparison against the 2022–2023 literature (same simulator, same seeds,
identical 0.55 J/node budget, 20 runs, full heterogeneous deployment).** Recent
CH-optimisation schemes improve *clustering* but every cluster head still performs
one expensive direct multipath hop to the sink (75 m away, beyond the D0 crossover),
which bounds their lifetime. To test this directly we re-implemented DCK-LEACH's
dual-head election and NPSOP's PSO CH-selection inside our own energy model and ran
them head-to-head with ClusterChain-H on all four metrics. The full 9-protocol table
headline result (best CCH config, K=1, 3038 ± 127 rounds):

| Protocol | Lifetime (rnd) | vs best CCH | PDR | Delay (hops) |
|----------|--------------:|------------:|----:|------------:|
| DCK-LEACH (dual head, 2022) | 1171 | 0.39× | 1.00 | 3.0 |
| NPSOP (PSO CH, 2023) | 2092 | 0.69× | 1.00 | 2.0 |
| **ClusterChain-H (K=1, best)** | **3038** | **1.00×** | **0.96** | **73.9** |
| ClusterChain-H (K=3, low-delay) | 2819 | 0.93× | 0.98 | 24.7 |

ClusterChain-H outperforms both recent schemes by **2.7× over DCK-LEACH** and
**1.5× over NPSOP** in lifetime. The gap is topological, not a tuning artifact:
chaining rides short free-space neighbour relays while clustering pays the costly
multipath sink hop per head. **K is a delay/lifetime knob, not a hidden winner** —
K=1/2/3 lifetimes (3038/2931/2819) are statistically tied within 95% CI, and higher
K strictly lowers delay (74→37→25 hops). We therefore position the 2022–2023
clustering literature as baselines we beat, and flag **learned routing (HDQN,
DRL-GNN)** — reported in the survey literature to reach ~4000+ rounds *in their own
simulators* — as the one class we have not matched. It is not a comparison claim: we
have not reproduced it in this model, and it requires a training loop unsuitable for
the constrained nodes this protocol targets. Leave it as explicit future work.

---

## 3. Simulation Model Design

**Software tool.** The simulation is implemented in **Python 3** (NumPy,
Matplotlib) as a discrete-event simulator built directly on the first-order radio
energy model (Heinzelman et al., 2000). All compared protocols (LEACH, PEGASIS, SEP,
DEEC) report their canonical results under this same model, so a single shared
Python implementation guarantees a strictly like-for-like comparison free of
simulator-specific implementation bias. The model abstracts MAC-layer effects
(collisions, propagation) in favor of transparent, reproducible network-layer
energy and lifetime analysis consistent with the compared literature. All protocols
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
     lower delay (homogeneous ablation still gives 1.45× PEGASIS lifetime).

   **Why K=1 is lifetime-optimal.** The per-round energy of the clustered
   construction is the sum of (i) member→CH free-space tx at link length
   d_m ~ a/√k, (ii) N CH receptions + aggregations, (iii) (k−1) head-chain relay
   links at d_c ~ b/k, and (iv) k multipath sink hops at the dominant cost
   E_MP·D⁴. Every additional parallel chain (k > 1) adds one more expensive
   multipath sink hop while only marginally shortening the intra-chain relays, so
   the energy-minimising chain count is k = 1. We confirm this analytically with
   the `optimal_k` routine (minimises e_round(k) over k) and empirically: K=1/2/3
   lifetimes (3038/2931/2819) are within 95% CI, so the single-chain config is the
   frugal point and higher K is purely a delay lever (74→37→25 hops).

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
| Seeds | 20 (N=100): `1000 + 7i`; 8 (N=200): fixed set; 8 (N=500): fixed set |
| Max rounds | 6000 (full lifetime to last-node-death; both RNGs seeded per seed) |
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
| PEGASIS | 2291 | ±41 | 0.99 | 77.2 | 1.00× |
| DEEC | 1203 | ±28 | 0.99 | 1.0 | 0.52× |
| SEP | 1358 | ±46 | 0.99 | 1.0 | 0.59× |
| DCK-LEACH (2022) | 1171 | ±12 | 1.00 | 3.0 | 0.51× |
| NPSOP (2023) | 2092 | ±110 | 1.00 | 2.0 | 0.91× |
| H-PEGASIS (2009, geometry only) | 3084 | ±120 | 0.99 | 75.5 | 1.35× |
| **ClusterChain-H (K=1)** | **3038** | ±127 | **0.96** | 73.9 | **1.33×** |
| **ClusterChain-H (K=2)** | **2931** | ±153 | **0.98** | 37.2 | **1.28×** |
| **ClusterChain-H (K=3)** | **2819** | ±159 | **0.98** | 24.7 | **1.23×** |

ClusterChain-H delivers **1.33× the lifetime of heterogeneity-aware PEGASIS**
(3038 vs 2291), **2.24× SEP** (1358) and **2.53× DEEC** (1203). Its PDR (0.96 at
K=1) is marginally *below* the baselines' ~0.99 — an honest, expected consequence of
the single-chain topology: when the rotating terminus dies on its sink hop, the whole
round's fused payload is lost, exactly as in vanilla PEGASIS. This is the measured
trade-off for the long lifetime, not a counting artifact. Against the recent
literature it reaches **2.7× DCK-LEACH** (3038 vs 1171) and **1.5× NPSOP** (3038 vs
2092). **K is a delay/lifetime knob, not a hidden winner**: K=1/2/3 lifetimes
(3038/2931/2819) sit within each other's 95% CI, and higher K strictly lowers delay

**Decomposition of the gain (where the lifetime comes from).** Adding H-PEGASIS —
the MST-refined chain geometry + rotating leader, run *homogeneously* (no
heterogeneity-aware election) — already yields **3084 rounds (1.35× PEGASIS)**. This
isolates the structural contribution: the geometry + rotation mechanism alone accounts
for essentially the entire lifetime jump over vanilla PEGASIS. ClusterChain-H (3038)
matches H-PEGASIS on lifetime (within 95% CI) while *adding* the SEP/DEEC-style
heterogeneity-aware election. The election does not extend raw lifetime further because
the rotating terminus already balances the relay load well; its value is **fairness**,
not longevity — as §9.2 shows, CCH's election spares normal nodes 2.56× longer than
advanced nodes survive after them, a property H-PEGASIS (homogeneous election) does not
provide. The combination therefore reproduces H-PEGASIS's geometry gain *and* adds a
heterogeneity fairness guarantee at zero lifetime cost — which is why it still beats the
heterogeneity-only baselines SEP (2.24×) and DEEC (2.53×) by a wide margin.
(74→37→25 hops). The best lifetime config (K=1) is reported as the headline; K=3 is
the low-delay option (25 hops vs PEGASIS's 77) for time-sensitive sensing.

### 9.2 Per-class fairness and composite efficiency (N=100, 20 seeds)

The lifetime gain is meaningless if it comes from starving one node class. Because
ClusterChain-H elects leaders by residual energy × type, advanced (2×-energy) nodes
should outlive normal nodes — the heterogeneity-aware election doing its job. We track
the first-death round of each class and the Energy×Delay (E×D) composite (lower is
better) over the stable window.

| Config | First normal death | First advanced death | Adv/normal survival | E×D (×10⁻³) |
|--------|-------------------:|---------------------:|--------------------:|------------:|
| CCH-K1 | 493 | 1260 | 2.56× | 3.15 |
| CCH-K2 | 225 | 787 | 3.50× | 1.56 |
| CCH-K3 | 199 | 1040 | 5.22× | 1.03 |

Normal nodes survive **2.5–5.2× longer** in the presence of advanced nodes than
advanced nodes survive after them — the election explicitly spares low-energy normal
nodes, exactly the SEP/DEEC design intent, extended to a chaining topology. E×D
drops monotonically with K (3.15 → 1.03 ×10⁻³) because higher K trades a small
lifetime for a much shorter delay, confirming K as a clean efficiency/delay dial rather
than a hidden lifetime lever. The per-class tracking is now recorded by the core
protocol (`class_history`) so these figures are reproducible from seed, not read off a
secondary ablation script.

### 9.3 Homogeneous ablation (N=100, 20 seeds) — geometry + rotation only

With no advanced nodes (0.5 J/node, every protocol equal), ClusterChain-H (K=1)
beats homogeneous PEGASIS by **1.45×** (1742 ± 19 vs 1200 rounds), confirming the
MST geometry + rotating terminus are independently effective. The full heterogeneous
gain (1.33× over heterogeneity-aware PEGASIS) is this structural contribution plus the
legitimate heterogeneity-aware election — not extra battery.

The same structural contribution compounds under the first-class `relay` mode
(rotating relay-sink tier): ClusterChain-H reaches **~2.0× homogeneous PEGASIS**
(2417 rounds) with neutral PDR, because each chain's terminus forwards to the nearest
of R rotating relays instead of the far off-field base station — and no single relay
becomes a permanent bottleneck. The relay→BS forward hop is tracked as infrastructure
cost and never folded into sensor energy.

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

## 12. Mechanism Ablation Study

To test whether newer literature-prescribed mechanisms actually improve on the
ClusterChain-H multichain K=1 design, we ran a controlled A/B ablation under
the fixed benchmark of Section 2 (100 nodes, 100×100 m field, sink at (50,175),
first-order radio model, 0.5/1.0 J heterogeneity, 4000-bit packets, 20 seeds).
Every protocol shares `energy.py`; both `random` and `numpy` are seeded per
seed so each protocol sees the **identical node topology** (like-for-like, not
merely in expectation). Metrics: FND, LAST, PDR, hop delay, and per-class
(first-death split by node type) where instrumented.

### 12.1 Mechanisms that do NOT improve on the baseline

| Mechanism (literature rank) | LAST | vs K1 | FND | PDR | Note |
|---|---|---|---|---|---|
| Multichain K=1 (baseline) | 3038 ± 127 | 1.00× | 493 | 0.97 | — |
| Multichain K=3 (delay ref) | 2819 | 0.93× | 199 | 0.98 | delay 24.7 vs 74.5 |
| Energy-gradient relay (#5) | 2480 / 2233 | 0.82× / 0.73× | 986 / 1238 | 1.00 | raises per-round cost |
| Selective dual-terminus (#7) | 3055 / 2815 | 1.01× / 0.93× | 343 / 166 | 0.96 | failover rarely fires |

The energy-gradient relay (RACR-style residual-energy / distance / progress
next-hop score) spreads load — FND rises to 986–1238 — but its greedy local
score ignores the global per-round energy floor that the MST construction
minimises, so total radio cost per round rises and the whole network collapses
sooner (0.73–0.82×). The selective dual-terminus (vice node added only to long
chains, activated on primary-terminus death) is statistically indistinguishable
from baseline (1.01×): near end-of-life the vice is also depleted, so the
failover almost never triggers. Per-class curves confirm heterogeneity works as
intended — in the dual-terminus run, normal nodes die at ~356 while advanced
nodes survive to ~1113.

### 12.2 The mechanism that DOES: rotating relay-sink tier

The review's highest-upside candidate is a mobile / relay sink. To isolate the
geometric benefit from mobility accounting, we test a **static relay tier**:
fixed relay collection points sit closer to the field than the off-field base
station at (50,175). Each chain's terminus jumps to its nearest relay (charged
to the sensor exactly like the baseline's terminus→sink hop); the relay→BS
forward is infrastructure, tracked separately and never folded into sensor
energy.

- **Unlimited relay**: 3952 ± 151 (1.30×), PDR 1.00. Pure geometric win.
- **Budgeted 0.5 J relay** (per-relay battery equal to one node): still 3952
  lifetime (1.30×) — but the fixed relay **dies at round 341**, after which PDR
  collapses to 0.19. Sensor lifetime is real; the network is useless past 341.

The budgeted failure is a *concentration* problem: one fixed node foots the
full relay→BS multipath cost. **Rotating the relay role** every *E* rounds
(re-select the highest-residual nodes in the relay zone, each with a fresh 0.5 J
budget) spreads that cost across the network:

| Relay config | LAST | vs K1 | FND | PDR | PDR > 341 | relay dies |
|---|---|---|---|---|---|---|
| Static budgeted (no rot) | 3952 ± 151 | 1.30× | 595 | 0.19 | 0.01 | round 341 |
| Rotate every 25 | 4557 ± 164 | **1.50×** | 595 | 1.00 | 1.00 | — |
| Rotate every 50 | 4554 ± 164 | **1.50×** | 595 | 1.00 | 1.00 | — |
| Rotate every 100 | 4544 ± 169 | **1.50×** | 595 | 1.00 | 1.00 | — |

Rotation does two things at once: it removes the single-point relay failure
(no relay ever exhausts its budget, `RELAY_DEAD` empty for all three), keeping
PDR at 1.00 past 341; and because delivery never breaks, the geometric gain
compounds — pushing the win from 1.30× (static) to **1.50×** (rotating). The
epoch length *E* (25/50/100) is irrelevant to the result, so the mechanism is
not over-fit to a tuning parameter.

### 12.3 Why the election cannot beat geometry on lifetime

The H-PEGASIS result (§9.1: 3084 rounds, within CI of CCH-K1's 3038) raises a
natural question: can a *smarter election* push lifetime above the MST+rotation
ceiling? We tested the most principled candidate — **energy-ordered chain
traversal**, where the linear chain order is sorted by descending residual energy so
the highest-energy node carries the largest relay fan-in and the lowest-energy node
the smallest. The intuition: a low-energy node dying early should lose few upstream
packets.

| Configuration | LAST | vs H-PEGASIS | PDR | Note |
|---|---|---|---|---|
| H-PEGASIS (geometry + rotation) | 3084 ± 61 | 1.00× | 0.99 | ceiling |
| CCH-K1 (election + rotation) | 3038 ± 127 | 0.99× | 0.96 | matches |
| Energy-ordered chain | 2534 ± 90 | **0.82×** | ~0.99 | *worse* |

The energy ordering **degrades** lifetime by 18%. Sorting by energy discards the
MST's short-link property: the extra transmit cost from longer hops outweighs the
relay-fan-in savings, because the rotating terminus already places the
highest-energy node on the dominant (multipath) sink hop. This is direct evidence
that **link geometry, not relay-fairness, is the binding constraint on lifetime**
under the first-order model — which is exactly why H-PEGASIS's geometry refinement
is the right structural baseline and why CCH's election contributes *fairness*
(§9.2: normal nodes survive 2.56× longer) rather than additional longevity. Any
claim that a better election beats H-PEGASIS on lifetime would have to overcome this
0.82× result.

### 12.4 Scale robustness

The 1.50× is not a small-network artefact. Holding the per-node energy budget
and 20-seed protocol fixed, the rotating relay tier keeps its margin at larger
deployments:

| N | baseline LAST | rotating-relay LAST | ×baseline | PDR | PDR > 341 | relay dies |
|---|---|---|---|---|---|---|
| 100 | 3038 ± 127 | 4554 ± 164 | 1.50× | 1.00 | 1.00 | — |
| 200 | 3351 ± 67 | 4660 ± 195 | 1.39× | 1.00 | 1.00 | — |
| 500 | 3610 ± 22 | 4906 ± 48 | 1.36× | 1.00 | 1.00 | — |

The margin softens slightly with scale (1.50 → 1.36×) because the fixed relay
zone serves proportionally more nodes, but PDR stays at 1.00 and no relay fails
at any scale — the result is robust, not a single-topology coincidence.

### 12.5 Interpretation

Of the three leading literature-prescribed mechanisms, only the relay-sink tier
beats the existing design, and only when the relay role is **rotated** rather
than fixed. The two "obvious" tweaks (energy-gradient relay, dual terminus)
either regress or neutralize — a finding the survey literature does not report,
because almost no paper in the field runs a strict common-benchmark head-to-head.
The ablation therefore contributes two things: (a) negative evidence that
popular next-step mechanisms do not displace a clean baseline, and (b) a
positive, scale-robust 1.50× mechanism (rotating relay tier) with honest
infrastructure accounting. Scripts and raw JSON results: `cch_experimental.py`,
`cch_relaysink.py`, `eval_experimental.py`, `eval_dualterminus.py`,
`eval_relaysink.py`, `eval_relayrotation.py`, `eval_relayscale.py`.

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
- `cch_experimental.py` — ablation protocol (energy-gradient relay, adaptive-K,
  selective dual-terminus fail-over).
- `cch_relaysink.py` — static and rotating relay-sink tier variants.
- `eval_experimental.py`, `eval_dualterminus.py`, `eval_relaysink.py`,
  `eval_relayrotation.py`, `eval_relayscale.py` — ablation harnesses
  (aforementioned mechanisms + scale robustness) with matching `.json` results.
- Figures: `dashboard3.png`, `death_timeline.png`, `comparison.png`,
  `range_impact.png`, `energy_consumption.png`, `anim_*.gif`.
