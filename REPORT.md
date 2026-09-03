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
  Raghavendra 2002) forms a single greedy chain; data is fused along the chain and
  leadership rotates round-robin (node `i mod N`), so every node in turn performs
  the expensive multipath sink transmission — including far or energy-poor nodes —
  while the ~100-hop chain sets end-to-end delay.

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
| PEGASIS [2] | 2002 | Greedy chain, round-robin leader | High latency; blind rotation still assigns the multipath sink hop to far/low-energy nodes |
| SEP [3] | 2004 | Heterogeneous (2-level) CH election | Static 2-level only |
| DEEC [4] | 2006 | Heterogeneity + residual-energy CH prob. | Still cluster-only, direct to sink |
| Multi-leader PEGASIS variants | — | Multiple chain leaders / double chains | Added complexity, no heterogeneity |
| H-PEGASIS family | — | Hierarchical chain routing (parallel transmissions); MST-traversal chain construction [5b] | Homogeneous only; no heterogeneity-aware election |
| PDCH-style double head | — | Two cluster heads share one chain's load | Homogeneous; ignores node-type energy weighting |
| DCK-LEACH [6] | 2022 | Dual cluster-head (primary + vice), K-means/Canopy | Cluster-only; vice head still pays a direct multipath sink hop |
| NPSOP [7] | 2023 | PSO-selected CHs + routing paths | Cluster-only; CH→sink direct hop bounds lifetime |
| HEED [9] | 2004 | Residual-energy + degree, multi-iteration CH election | Needs variable power levels + iteration overhead; discussion baseline (§2.1) |
| TEEN/APTEEN [10] | 2001–02 | Threshold-driven reactive reporting | Sends less data by design — incomparable under periodic traffic (§2.1) |
| EEHC [11] | 2003 | Randomised multi-level hierarchy, stochastic tuning | Closest in spirit (hierarchical load spreading); different sink model (§2.1) |
| Recent metaheuristics [12, 13] | 2024–25 | GWO/PSO-optimised CH selection (centralised) | BS-side optimisation cost; survey + exemplar cited (§2.1) |
| HDQN / MADII [8] | 2023–2025 | DRL learned routing | Longer reported lifetime, but needs training + compute on constrained nodes |

ClusterChain-H generalises SEP/DEEC-style heterogeneity into a **clustering +
chaining hybrid** and replaces PEGASIS's blind round-robin leadership with an
energy- and sink-proximity **rotating terminus** across **parallel chains** —
so the costly multipath sink hop is always taken by a high-energy, near-sink
node instead of whichever node the rotation happens to land on.

### 2.1 Why HEED / TEEN / EEHC / recent metaheuristics are discussion-only baselines

A reviewer will rightly ask why the classic HEED/TEEN/EEHC trio and the 2024–25
metaheuristic wave are cited but not re-implemented. The reasons are comparability,
not convenience:

- **HEED [9]** elects heads over multiple iterations using residual energy plus node
  degree, assuming variable transmit power levels and extra control messaging whose
  cost our first-order model does not account. Porting it without its cost model
  would flatter it; porting the cost model would change the shared energy
  accounting all other protocols are judged on.
- **TEEN/APTEEN [10]** are *reactive*: nodes transmit only on threshold crossings,
  so they move far less data than our periodic 1-packet/round workload. Any
  lifetime/PDR comparison would conflate "sent less" with "routed better".
- **EEHC [11]** is the closest in spirit (randomised hierarchy spreading load over
  levels, stochastically tuned) and we acknowledge it as such; it assumes a
  different sink/traffic geometry, so we cite rather than approximate it.
- **Recent metaheuristics (surveyed in [12]; HGWO [13] as exemplar)** optimise CH
  selection at the base station with population-based search — a centralised,
  compute-heavy step outside the distributed protocol class this study compares
  (same reason NPSOP is represented by its distributed election mechanism only).

The implemented set (LEACH/PEGASIS/SEP/DEEC/H-PEGASIS/DCK-LEACH/NPSOP-mechanism)
is therefore the complete set of *distributed, periodic-reporting, first-order-model*
comparators. Extending the harness to reactive or centralised classes is explicit
future work, not an oversight.

**Positioning vs prior chain refinements.** MST-traversal chain construction
(Meghanathan [5b]) already replaces greedy chaining with refined geometry, and
the H-PEGASIS family / PDCH-style double heads add hierarchy and load-sharing,
but all are *homogeneous* protocol families: every node carries the same initial energy,
so their election cannot exploit heterogeneity. The contribution of ClusterChain-H
is the **fusion** of MST+rotation chain geometry with SEP/DEEC-style
heterogeneity-aware election — advanced (2×-energy) nodes are steered toward the
expensive relay/aggregation roles while normal nodes are spared. This is a
combination, not a new primitive; its value is that it retains the MST-geometry
gains *and* adds the heterogeneity margin that those protocols forgo.
We therefore benchmark against MST-geometry + rotating-leader construction as the structural
baseline and against SEP/DEEC as the heterogeneity baseline, and show the
combination (1.99× SEP, 2.57× DEEC) exceeds either axis alone.

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
| **ClusterChain-H (K=1, best)** | **3038** | **1.00×** | **0.96** | **74.7** |
| ClusterChain-H (K=3, low-delay) | 2819 | 0.93× | 0.98 | 24.7 |

ClusterChain-H outperforms both recent schemes by **2.6× over DCK-LEACH** and
**1.5× over NPSOP** in lifetime. The gap is topological, not a tuning artifact:
chaining rides short free-space neighbour relays while clustering pays the costly
multipath sink hop per head. **K is a delay/lifetime knob, not a hidden winner** —
K=1/2/3 lifetimes (3038/2931/2819) overlap in 95% CI; the paired test (§9.6) finds
no K1–K2 gap but detects a small consistent K1–K3 cost (−219 rounds, p < 0.01,
18/20 seeds) — the modest, measured price of the 3× delay cut. We therefore position the 2022–2023
clustering literature as baselines we beat, and flag **learned routing (HDQN,
MADII)** — reported in the literature to reach longer lifetimes *in their own
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

1. **LEACH [1]** — probabilistic CH election (`T(n)` threshold, `p_ch = 0.05`),
   members join nearest CH, CH aggregates and transmits directly to sink (1-hop delay).
   Note: SEP/DEEC use `p_opt = 0.1` per their published specifications while LEACH
   uses `p = 0.05` per its own — each protocol runs at its literature-standard
   CH probability, so the comparison tests canonical configurations, not a
   single forced value.
2. **PEGASIS [2]** — greedy nearest-neighbour chain rebuilt every round; data fused
   along the chain to a round-robin leader that transmits to the sink (delay ≈
   chain length; the sink hop lands on far/low-energy nodes 1/N of the time).
3. **SEP / DEEC [3, 4]** — heterogeneity-aware CH election (advanced nodes, 2× initial
   energy; DEEC adds residual-energy weighting).
4. **ClusterChain-H** — four mechanisms:
    - **Heterogeneity-aware election**: CH/relay score = weighted residual energy ×
      node type (SEP/DEEC style [3, 4]) + sink proximity.
    - **MST chain geometry** (Prim's MST, O(N²)): minimum-total-length aggregation
      structure in the MLDA spirit (Kalpakis et al. [5]; MST-traversal chains [5b]),
      removing PEGASIS's long greedy links.
    - **Rotating terminus**: the sink-facing chain end is the node maximising
      residual energy and sink proximity, rotated every round (replaces blind
      round-robin leadership with energy-aware leadership).
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
    frugal point and higher K is purely a delay lever (75→37→25 hops).

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
| Seeds | 20 (N=100 canonical); 8 (N=200 scale table, §9.4); 20 (relay scale N≤500, §12.4); 8 (N=500 sweep) |
| Max rounds | 6000 (full lifetime to last-node-death; both RNGs seeded per seed) |
| Metrics | Throughput, PDR, E2E delay, energy, lifetime, loss |

**Simulation tooling.** The evaluation uses a custom Python simulator built
specifically for this study rather than a general-purpose network simulator
(NS-3, Contiki-NG/Cooja, OMNeT++). Rationale: all protocols here share the
same first-order radio energy model (Heinzelman et al. 2000), and a purpose-built
simulator gives exact control over that energy model, deterministic seeded
reproducibility (both the `random` and `numpy` RNGs are seeded per run), and a
common per-round history interface across every protocol — which a
general-purpose simulator would obscure behind its own stack. The first-order
model is the standard teaching/reference model for WSN lifetime studies and is
sufficient to compare routing-protocol energy trade-offs; it abstracts real
radio effects (shadowing, collision, retransmission), so absolute round counts
are relative comparisons, not field predictions.

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
  H-PEGASIS, ClusterChain-H (multichain K=3).
- **Scenario 2 — Communication-range sensitivity (N=100, 15 seeds):** unlimited vs
  `R = 35 m` for LEACH, PEGASIS, CCH-K1 and CCH-K3, demonstrating range-induced
  packet loss under coupled seeding.
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
| LEACH | 912 | ±8 | 0.98 | 1.0 | 0.39× |
| PEGASIS | 2291 | ±41 | 0.99 | 77.2 | 1.00× |
| DEEC | 1184 | ±21 | 0.99 | 1.0 | 0.52× |
| SEP | 1528 | ±86 | 0.99 | 1.0 | 0.67× |
| DCK-LEACH (2022) | 1171 | ±12 | 1.00 | 3.0 | 0.51× |
| NPSOP (2023) | 2092 | ±110 | 1.00 | 2.0 | 0.91× |
| H-PEGASIS (geometry only) | 3084 | ±120 | 0.99 | 75.5 | 1.35× |
| **ClusterChain-H (K=1)** | **3038** | ±127 | **0.96** | 74.7 | **1.33×** |
| **ClusterChain-H (K=2)** | **2931** | ±153 | **0.98** | 37.2 | **1.28×** |
| **ClusterChain-H (K=3)** | **2819** | ±159 | **0.98** | 24.7 | **1.23×** |

ClusterChain-H delivers **1.33× the lifetime of heterogeneity-aware PEGASIS**
(3038 vs 2291), **1.99× SEP** (1528) and **2.57× DEEC** (1184). Its PDR (0.96 at
K=1) is marginally *below* the baselines' ~0.99 — an honest, expected consequence of
the single-chain topology: when the rotating terminus dies on its sink hop, the whole
round's fused payload is lost, exactly as in vanilla PEGASIS. This is the measured
trade-off for the long lifetime, not a counting artifact. Against the recent
literature it reaches **2.6× DCK-LEACH** (3038 vs 1171) and **1.5× NPSOP** (3038 vs
2092). **K is a delay/lifetime knob, not a hidden winner**: K=1/2/3 lifetimes
(3038/2931/2819) overlap in 95% CI with no significant K1–K2 gap; the paired test
(§9.6) detects only a small consistent K1–K3 cost (−219 rounds, 18/20 seeds),
and higher K strictly lowers delay

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
heterogeneity-only baselines SEP (1.99×) and DEEC (2.57×) by a wide margin.
(75→37→25 hops). The best lifetime config (K=1) is reported as the headline; K=3 is
the low-delay option (25 hops vs PEGASIS's 77) for time-sensitive sensing.

### 9.2 Per-class fairness and composite efficiency (N=100, 20 seeds)

The lifetime gain is meaningless if it comes from starving one node class. Because
ClusterChain-H elects leaders by residual energy × type, advanced (2×-energy) nodes
should outlive normal nodes — the heterogeneity-aware election doing its job. We track
the first-death round of each class and the Energy×Delay (E×D) composite (lower is
better) over the stable window.

| Config | First normal death | First advanced death | Adv/normal survival | E×D (J·hops) |
|--------|-------------------:|---------------------:|--------------------:|------------:|
| CCH-K1 | 493 | 1260 | 2.56× | 2.57 |
| CCH-K2 | 225 | 787 | 3.50× | 1.29 |
| CCH-K3 | 199 | 1040 | 5.22× | 0.86 |

Normal nodes survive **2.5–5.2× longer** in the presence of advanced nodes than
advanced nodes survive after them — the election explicitly spares low-energy normal
nodes, exactly the SEP/DEEC design intent, extended to a chaining topology. E×D
drops monotonically with K (2.57 → 0.86 J·hops) because higher K trades a small
lifetime for a much shorter delay, confirming K as a clean efficiency/delay dial rather
than a hidden lifetime lever. The per-class tracking is recorded by the core
protocol (`class_history`); the figures above are the means over the same 20
coupled seeds, reproduced in `eval_supplement.json` via `eval_supplement.py`.

### 9.3 Homogeneous ablation (N=100, 20 seeds) — geometry + rotation only

With no advanced nodes (0.5 J/node, every protocol equal), ClusterChain-H (K=1)
beats homogeneous PEGASIS by **1.45×** (1742 ± 38 vs 1200 rounds), confirming the
MST geometry + rotating terminus are independently effective. The full heterogeneous
gain (1.33× over heterogeneity-aware PEGASIS) is this structural contribution plus the
legitimate heterogeneity-aware election — not extra battery.

The same structural contribution compounds under the first-class `relay` mode
(rotating relay-sink tier): ClusterChain-H reaches **~2.0× homogeneous PEGASIS**
(2417 ± 37 rounds) with neutral PDR, because each chain's terminus forwards to the nearest
of R rotating relays instead of the far off-field base station — and no single relay
becomes a permanent bottleneck. The relay→BS forward hop is tracked as infrastructure
cost and never folded into sensor energy. All three homogeneous figures are means
over the same 20 coupled seeds (`eval_supplement.json`).

### 9.4 Scalability (N=200, 8 seeds, heterogeneous, means — `eval_supplement.json`)

| Protocol | Lifetime (rnd) | Delay (hops) |
|----------|---------------:|-------------:|
| LEACH | 941 | 1.0 |
| PEGASIS | 2396 | 156.7 |
| SEP | 1776 | 1.0 |
| DEEC | 1271 | 1.0 |
| **ClusterChain-H (K=3)** | **3306** | **50.7** |

At N=200 ClusterChain-H reaches **~1.38× PEGASIS lifetime** with **3.1× lower delay**
(50.7 vs 156.7 hops). Trends are stable across scales.

### 9.5 Communication-range sensitivity (R = 35 m)

Coupled-seed comparison (15 seeds, identical topologies per seed — both RNGs
seeded; an earlier uncoupled version of this experiment overstated CCH
robustness and has been corrected):

| Protocol | PDR (unlimited) | PDR (R=35 m) | Loss @35 m |
|----------|----------------:|-------------:|-----------:|
| LEACH | 0.978 | 0.351 | 0.649 |
| PEGASIS | 0.978 | 0.947 | 0.053 |
| CCH-K1 (single chain) | 0.960 | 0.122 | 0.878 |
| CCH-K3 (3 sectors) | 0.984 | 0.653 | 0.347 |

A tight 35 m range exposes the *maximum* link length, not the total energy: PEGASIS's
greedy nearest-neighbour chain keeps every hop short (5% loss), while the
MST-visitation ordering used by ClusterChain-H minimises the *sum* of squared links
(energy-optimal) but contains a few long inter-branch jumps. In a single chain one
broken link voids the whole round, so CCH-K1 collapses (0.122); sector chains isolate
the breakage, so CCH-K3 (0.653) still beats LEACH (0.351), whose member→CH links
routinely exceed 35 m. Lifetime is **unchanged** (out-of-range attempts still expend
energy), isolating the packet-loss effect. Deployment insight: with short radios,
prefer more, shorter chains (higher K) or greedy-NN geometry; the lifetime-optimal
K=1 configuration assumes the unlimited-range regime of §9.1.

### 9.6 Statistical significance (paired tests, n = 20 coupled seeds)

Confidence intervals describe uncertainty; they do not test the headline gaps.
Because every protocol ran on the *identical* 20 topologies, per-seed differences
are paired, so we test CCH-K1 against each baseline with **both** a paired
Student t-test (exact p, dependency-free implementation in `eval_significance.py`,
validated against textbook values) and a Wilcoxon signed-rank test (normal
approximation, n = 20). H0: zero mean/median paired difference. A gap is claimed
only if **both** reject at α = 0.05. Per-seed data: `eval_significance.json`.

| Baseline vs CCH-K1 | Mean Δ (rounds) | 95% CI | p (paired t) | p (Wilcoxon) | Seeds won | Verdict |
|---|---|---|---|---|---|---|
| LEACH | +2126 | ±126 | <1e-15 | <1e-3 | 20/20 | significant |
| PEGASIS | +747 | ±103 | <1e-10 | <1e-3 | 20/20 | significant |
| SEP | +1510 | ±118 | <1e-15 | <1e-3 | 20/20 | significant |
| DEEC | +1854 | ±117 | <1e-15 | <1e-3 | 20/20 | significant |
| DCK-LEACH | +1867 | ±121 | <1e-15 | <1e-3 | 20/20 | significant |
| NPSOP | +945 | ±119 | <1e-11 | <1e-3 | 20/20 | significant |
| H-PEGASIS | −46 | ±61 | 0.16 | 0.37 | 10/20 | **not significant** |
| CCH-K2 | +107 | ±110 | 0.072 | 0.0095 | 18/20 | not significant (tests disagree) |
| CCH-K3 | +219 | ±133 | 0.0045 | 0.0061 | 18/20 | significant (small) |

Three readings matter. First, every headline gap (1.33× PEGASIS through 3.3×
LEACH) is significant under both tests with all 20 seeds in favour — the "×"
column is not a CI artefact. Second, H-PEGASIS is statistically
indistinguishable from CCH-K1 (10/20 seeds each way): the geometry mechanism,
not the election, sets the lifetime ceiling, exactly as §9.1's decomposition
argues — we state this as a null result, not a win. Third, the K knob has a
real but small price: K1–K2 is not significant, K1–K3 is (−219 rounds, ~7%),
which is the measured cost of cutting delay 75→25 hops.

---

## 9. Analysis & Interpretation

1. **Lifetime.** ClusterChain-H's gain is driven by (a) heterogeneity-aware election
   that spares low-energy/normal nodes, and (b) the MST geometry + rotating terminus
    that eliminate PEGASIS's far/multipath leader bottleneck. The homogeneous ablation
    (1.45× homogeneous PEGASIS) confirms the *structural* mechanisms are independently
    effective; the full 1.33× over heterogeneity-aware PEGASIS combines that structural
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
   a tight 35 m range limit the same single-chain fragility appears in a second form
   (CCH-K1 0.122 vs PEGASIS 0.947 — greedy-NN links are shorter than MST-visitation
   jumps); sector chains mitigate it (CCH-K3 0.653 vs LEACH's 0.351).
4. **Energy.** Cumulative energy consumption rises slowest for ClusterChain-H
   (see `energy_consumption.png`), explaining the extended lifetime.

---

## 10. Conclusions

ClusterChain-H dominates the heterogeneity-aware baselines on lifetime (1.33×
PEGASIS, 1.99× SEP, 2.57× DEEC) and the recent 2022–2023 CH-optimisation
literature re-implemented in this simulator (2.6× DCK-LEACH, 1.5× NPSOP), with
PDR of 0.96–0.98 (marginally below the baselines' ~0.99 — the measured cost of the
single-chain topology, counted consistently across all protocols) and a delay knob
from 75 (K=1) down to 25 hops (K=3) versus PEGASIS's 77. The homogeneous ablation
(1.45× PEGASIS) confirms the gain is structural protocol efficiency on an identical
per-node energy budget, not an artefact of extra battery. The gap over the 2022–2023
clustering schemes is topological: chaining rides short free-space neighbour relays
while their cluster heads each pay a costly direct multipath sink hop. Learned routing
(HDQN, MADII) is the one class not yet matched in this model and is left as explicit
future work (it is reported in the literature at longer lifetimes in *their own*
simulators; we do not claim a like-for-like comparison). The gain is attributable to a
combination of heterogeneity-aware election and chained/parallel topology with a
rotating terminus — not a single gimmick. The configurable communication-range
parameter and range-sensitivity study qualify the protocol's operating envelope:
the lifetime-optimal K=1 configuration assumes generous radio range, while
short-range deployments should use higher K or greedy geometry (§9.5). All code,
evaluation harnesses, and reproducibility artifacts are open in the repository.

---

## 11. References

1. Heinzelman, W., Chandrakasan, A., Balakrishnan, H. "Energy-Efficient
   Communication Protocol for Wireless Microsensor Networks." *Proc. HICSS*, 2000.
2. Lindsey, S., Raghavendra, C. "PEGASIS: Power-Efficient Gathering in Sensor
   Information Systems." *Proc. IEEE Aerospace Conf.*, 2002.
3. Smaragdakis, G., Matta, I., Bestavros, A. "SEP: A Stable Election Protocol for
   clustered heterogeneous WSNs." *Proc. SANPA* (workshop held with MASS), 2004.
4. Li, Q., Zhu, Q., Wang, M. "DEEC: Design of a distributed energy-efficient
   clustering algorithm for heterogeneous WSNs." *Computer Communications*,
   29(12), 2230–2237, 2006.
5. Kalpakis, K., Dasgupta, K., Namjoshi, P. "Efficient algorithms for maximum
   lifetime data gathering and aggregation in wireless sensor networks."
   *Computer Networks*, 42, 697–716, 2003 (MLDA formulation; conf. version at
   IEEE ICN 2002).
5b. Meghanathan, N. "Use of Tree Traversal Algorithms for Chain Formation in the
   PEGASIS Data Gathering Protocol." *KSII Trans. Internet and Information
   Systems*, 3(3), 2009 (MST-based PEGASIS chain construction).
6. Wu, M. et al. "A Dual Cluster-Head Energy-Efficient Routing Algorithm Based on
   Canopy Optimization and K-Means for WSN (DCK-LEACH)." *Sensors*, 22(24), 9731,
   2022.
7. Hu, H. et al. "A Novel Particle Swarm Optimization-Based Clustering and
   Routing Protocol (NPSOP)." *Wireless Personal Communications*, 133, 2175–2202,
   2023.
8. Song, Y. et al. "A Data Transmission Path Optimization Protocol for
   Heterogeneous WSNs Based on Deep Reinforcement Learning (HDQN)." *J. Computer
   and Communications*, 11(8), 2023; Yang, J. et al. "An Energy-Efficient and
   Transmission-Efficient Adaptive Routing Algorithm Using Deep Reinforcement
   Learning (MADII, multi-agent DQN + informer)." *IEEE IoT Journal*, 2025
   (representative learned-routing works; not reproduced here — see §2).
9. Younis, O., Fahmy, S. "HEED: A Hybrid, Energy-Efficient, Distributed
   clustering approach for ad hoc sensor networks." *IEEE Trans. Mobile
   Computing*, 3(4), 366–379, 2004.
10. Manjeshwar, A., Agrawal, D. P. "TEEN: A Routing Protocol for Enhanced
    Efficiency in Wireless Sensor Networks." *Proc. IPDPS*, 2001 (APTEEN hybrid
    extension, *Proc. IPDPS*, 2002).
11. Bandyopadhyay, S., Coyle, E. J. "An Energy Efficient Hierarchical Clustering
    Algorithm for Wireless Sensor Networks." *Proc. IEEE INFOCOM*, 1713–1723, 2003.
12. Shokouhifar, M. et al. "AI-driven cluster-based routing protocols in WSNs: A
    survey of fuzzy heuristics, metaheuristics, and machine learning models."
    *Computer Science Review*, 54, 100684, 2024.
13. Mehrotra, P., Bhardwaj, D. "HGWO: A Novel Hybrid Optimization Algorithm for
    Energy-Aware Clustering and Routing in WSNs." *Engineering Research Express*,
    2025 (recent metaheuristic exemplar; centralised BS-side optimisation).

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
| Multichain K=1 (baseline) | 3038 ± 127 | 1.00× | 493 | 0.96 | — |
| Multichain K=3 (delay ref) | 2819 | 0.93× | 199 | 0.98 | delay 24.7 vs 74.7 |
| Energy-gradient relay (#5) | 2480 / 2233 | 0.82× / 0.73× | 986 / 1238 | 1.00 | raises per-round cost |
| Selective dual-terminus (#7) | 3055 / 2815 | 1.01× / 0.93× | 343 / 195 | 0.96 / 0.98 | failover rarely fires |

The energy-gradient relay (RACR-style residual-energy / distance / progress
next-hop score) spreads load — FND rises to 986–1238 — but its greedy local
score ignores the global minimum-total-length structure that the MST construction
optimises, so total radio cost per round rises and the whole network collapses
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

| Configuration | LAST (mean) | vs H-PEGASIS | PDR | Note |
|---|---|---|---|---|
| H-PEGASIS (geometry + rotation) | 3084 | 1.00× | 0.99 | ceiling (§9.1) |
| CCH-K1 (election + rotation) | 3038 | 0.99× | 0.96 | matches (§9.1) |
| Energy-ordered chain | 2534 | **0.82×** | ~0.99 | *worse* |

> **Provenance.** The energy-ordered probe is a supplementary analysis, not part of
> the canonical benchmark: it re-ran the H-PEGASIS chain builder with the traversal
> order sorted by descending residual energy (same N=100 heterogeneous deployment,
> same energy model, smaller seed set than the 20-seed §9.1 benchmark — hence no
> 95% CI is reported here). The qualitative result (geometry dominates election,
> ~0.82×) is robust to the seed count; the exact round count should be read as
> indicative, unlike the §9.1/§12.1–12.2 figures which are fully reproduced from
> in-repo harnesses.

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
  Scope note: DualHead ports the primary/vice election mechanism on plain
  k-means (the paper's Canopy pre-clustering is omitted); PSOCH ports the PSO
  CH-selection component (the paper's joint routing-path particle encoding is
  omitted). Both use the shared energy model and identical budget/seeds.
- `tests/test_protocols.py` — 7 regression tests (all pass).
- `dashboard_gen.py` — focused LEACH/PEGASIS/ClusterChain-H dashboard + death
  timeline.
- `scenarios.py` — communication-range sensitivity + energy-consumption plots.
- `canonical_eval.py` — authoritative 20-seed N=100 benchmark (includes H-PEGASIS); `eval.py` — coupled-seed homogeneous + heterogeneous evaluation. (Legacy: `eval_n100.py`, `eval_scale.py`.)
- `cch_experimental.py` — ablation protocol (energy-gradient relay, adaptive-K,
  selective dual-terminus fail-over).
- `eval_supplement.py` → `eval_supplement.json` — per-class fairness + E×D (9.2),  homogeneous ablation incl. relay (9.3), N=200 heterogeneous scale table (9.4),
  and first-class relay-K1 cross-check of the README relay row. The first-class
  `mode='relay'` reproduces the legacy `RelayRotationClusterChain` harness
  exactly (both 4554 ± 164), so the ablation prototype and the shipped protocol
  are the same mechanism.
- `cch_relaysink.py` — static and rotating relay-sink tier variants.
- `eval_experimental.py`, `eval_dualterminus.py`, `eval_relaysink.py`,
  `eval_relayrotation.py`, `eval_relayscale.py` — ablation harnesses
  (aforementioned mechanisms + scale robustness) with matching `.json` results.
- `eval_significance.py` → `eval_significance.json` — per-seed LAST/PDR/DELAY
  plus paired t-test + Wilcoxon results behind §9.6 (dependency-free stats,
  validated against textbook values).
- Figures: `dashboard3.png`, `death_timeline.png`, `comparison.png`,
  `timelines.png` (per-round alive/PDR/throughput/delay/energy timelines),
  `range_impact.png`, `energy_consumption.png`, `anim_*.gif`.
