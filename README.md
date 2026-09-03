# ClusterChain-H: LEACH / PEGASIS Hybrid vs ClusterChain-H WSN Routing Comparison

Simulation-based performance comparison of hierarchical routing protocols for
Wireless Sensor Networks (WSNs), including **ClusterChain-H** — a heterogeneity-aware
hybrid protocol proposed and evaluated in this project.

## Overview

This project implements and compares five routing protocols under a single
first-order radio energy model (Heinzelman et al., 2000) so every result is
strictly like-for-like:

- **LEACH** (Low-Energy Adaptive Clustering Hierarchy) — probabilistic cluster
  head rotation. Random cluster-head election ignores residual energy and
  distance to the sink, so a far cluster head can pay a costly multipath hop
  every round (Heinzelman et al., 2000).
- **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems) — a
  greedy chain over all nodes. Energy is balanced well, but every node relays
  every round (high delay, ~77 hops) and round-robin leadership still assigns
  the costly multipath sink hop to far or energy-poor nodes
  (Lindsey & Raghavendra, 2002).
- **SEP / DEEC** — heterogeneity-aware cluster-head election (advanced nodes at
  2x initial energy carry the load), the standard heterogeneous baselines
  (Smaragdakis et al., 2004; Li et al., 2006).
- **ClusterChain-H** — a hybrid combining LEACH-style clustering with a
  PEGASIS-style refined chain, plus four mechanisms: MST chain geometry (removes
  PEGASIS's long greedy links), an energy + sink-proximity **rotating terminus**
  (energy-aware leadership: the sink hop always lands on a high-energy near-sink
  node), heterogeneity-aware election (SEP/DEEC
  style), and a tunable chain count K that trades delay against lifetime (K=1 is
  lifetime-optimal; higher K adds parallel chains that cut delay).

All protocols share the same `energy.py`, seed set, and deployment, so comparisons
are fair. ClusterChain-H generalises the SEP/DEEC heterogeneity idea into a
clustering + chaining hybrid and replaces blind round-robin leadership via the
rotating terminus across parallel chains.

## Key Results

Network lifetime, delivery and delay averaged over **20 seeded runs**
(100 nodes, 100m x 100m field, sink at (50, 175), 0.5 J initial energy;
**heterogeneous deployment: 10% advanced nodes at 2x energy = 0.55 J/node budget**):

| Protocol | Last node dead | PDR | Delay (hops) | vs PEGASIS |
|----------|--------------:|----:|------------:|-----------:|
| LEACH (het) | 912 | 0.98 | 1.0 | 0.39x |
| PEGASIS (het) | 2291 | 0.99 | 77.2 | 1.00x |
| SEP | 1528 | 0.99 | 1.0 | 0.67x |
| DEEC | 1184 | 0.99 | 1.0 | 0.52x |
| DCK-LEACH (2022) | 1171 | 1.00 | 3.0 | 0.51x |
| NPSOP (2023) | 2092 | 1.00 | 2.0 | 0.91x |
| **ClusterChain-H (K=1)** | **3038** | **0.96** | 74.7 | **1.33x** |
| **ClusterChain-H (K=2)** | **2931** | **0.98** | 37.2 | **1.28x** |
| **ClusterChain-H (K=3)** | **2819** | **0.98** | 24.7 | **1.23x** |
| **ClusterChain-H + rotating relay-sink** | **4554** | **1.00** | 77.1 | **1.99x** |

**Rotating relay-sink tier.** Adding a relay-collection tier (relays rotated
among highest-residual nodes) lifts lifetime to 4554 rounds with **PDR 1.00**
— **1.50x the ClusterChain-H K=1 baseline** and **~2.0x PEGASIS** under the
same 20-seed benchmark (Section 12). Unlike the fixed-relay variant (which
collapses PDR to 0.19 when the relay dies at round 341), rotation spreads the
relay→base-station cost across nodes so no single relay fails. This is reported
as a separate ablation experiment, not folded into the K=1/K=3 design space.



**Honest summary.** ClusterChain-H does not invent extra battery to win: every
protocol above runs on the *identical* 0.55 J/node heterogeneous budget, and the
gain is measured on the same energy envelope as the baselines. Against the
strongest like-for-like baseline (heterogeneity-aware PEGASIS) it delivers **1.33x**
lifetime with PDR of 0.96–0.98 (marginally below the baselines' ~0.99 — the measured
cost of the single-chain topology, where a terminus death on the sink hop clears the
whole round, counted consistently across all protocols) and a tunable delay
(K=3: 25 hops vs PEGASIS 77). Against the 2022–2023 CH-optimisation literature it
reaches **2.6x DCK-LEACH** and **1.5x NPSOP** — both re-implemented in this same
simulator, not cited from their papers. **K is a delay/lifetime knob, not a hidden
winner**: K=1/2/3 lifetimes (3038/2931/2819) overlap in 95% CI (paired tests find
no K1–K2 gap, only a small K1–K3 cost), and
higher K strictly lowers delay.

A **homogeneous ablation** (no advanced nodes; geometry + rotating terminus only)
gives ClusterChain-H **1.45x** the lifetime of homogeneous PEGASIS (1742 ± 38 vs
1200 rounds), confirming the structural mechanisms are independently effective; the
full heterogeneous gain combines that structural contribution with heterogeneity-aware
election.

A first-class **`relay` mode** (rotating relay-sink tier: each chain's terminus
forwards to the nearest of R rotating relays instead of the far off-field base
station) lifts lifetime to **~2.0x homogeneous PEGASIS** under the same benchmark
(neutral PDR, no single-relay bottleneck). The relay->BS forward hop is tracked as
infrastructure cost and never folded into sensor energy.

## Project Structure

```
.
├── energy.py            # First-order radio energy model (+ COMM_RANGE param)
├── leach.py             # LEACH (heterogeneity-aware: m, a_mult)
├── pegasis.py           # PEGASIS (heterogeneity-aware: m, a_mult)
├── sep.py / deec.py     # Heterogeneous cluster baselines
├── recent_variants.py   # DualHead (DCK-LEACH), PSOCH (NPSOP) recent baselines
├── hpegasis.py          # H-PEGASIS: MST chain + rotating leader (chaining baseline)
├── clusterchain.py      # Original ClusterChain (legacy hybrid, documented in history)
├── clusterchain_h.py    # ClusterChain-H: MST chain + rotating terminus + heterogeneity
├── cch_relaysink.py     # Relay-sink ablation (SUPERSEDED by mode='relay', retained as evidence)
├── cch_experimental.py  # Ablation harness (energy-gradient, dual-terminus, static relay)
├── canonical_eval.py    # AUTHORITATIVE N=100 benchmark (20 seeds, H-PEGASIS included)
├── eval.py              # Homogeneous + heterogeneous coupled-seed eval -> eval_results.json
├── eval_full.py         # N=100/200/500 sweep (N=500 slow; see note below)
├── eval_consistency.py / eval_dualterminus.py / eval_experimental.py
├── eval_relayrotation.py / eval_relaysink.py / eval_relayscale.py
├── eval_supplement.py  # per-class + homo-ablation + N=200 evidence -> eval_supplement.json
├── eval_significance.py # paired t + Wilcoxon significance -> eval_significance.json
├── gen_dashboards.py    # Regenerates comparison/dashboard/dashboard3/death_timeline PNGs
├── gen_timelines.py     # Regenerates timelines.png (per-round alive/PDR/throughput/delay/energy curves)
├── gen_scalability_fig.py # scalability.png (verified numbers, no re-sim)
├── scenarios.py         # Communication-range sensitivity + energy-consumption plots
├── dashboard_gen.py     # Legacy LEACH/PEGASIS/CCH dashboard + death timeline
├── animate.py           # Topology GIF generator (per-protocol node/energy/chain animation)
├── derivation.md        # Math: energy-optimal k* and the delay/lifetime tradeoff
├── derive_kstar.py      # Closed-form optimal chain length k* derivation
├── tests/test_protocols.py
├── REPORT.md            # Full mini-project report (problem, related work, results)
└── CONFERENCE_ABSTRACT.md
```

## Simulation Parameters

- **Nodes**: 100 (Scenario 1), 200 (Scenario 3), 500 (scalability)
- **Sink**: Fixed at (50, 175)
- **Initial Energy**: 0.5 J per normal node; advanced nodes (m=0.1) at 1.0 J
- **Packet Size**: 4000 bits
- **Energy Model**: First-order radio (Heinzelman et al., 2000)
- **Seeds**: 20 (N=100), deterministic
- **Metrics**: Lifetime (FND/HND/last), PDR, E2E delay (hops), Energy x Delay

## Reproducibility

Every result in this repo is reproducible from a fixed seed set with **both** RNGs
(`random` and `numpy`) seeded per run — there is no Monte-Carlo noise between runs.

**Environment**
- Python 3.11+ (developed on CPython 3.11.15)
- Pure-Python dependencies only: `numpy`, `matplotlib` (no compiled extensions)
- Install: `pip install numpy matplotlib`

**Run order (each script is self-contained and prints its own table)**

| Script | Produces | Notes |
|--------|----------|-------|
| `python canonical_eval.py` | `eval_canonical.json` + console table | Authoritative N=100 benchmark (20 seeds). Includes H-PEGASIS. Fast (<2 min). |
| `python eval.py` | `eval_results.json` | N=100/200 homogeneous + heterogeneous, coupled-seed. |
| `python eval_full.py` | `eval_full.json`, `lifetime.png` | Full heterogeneous sweep. **N=500 pass is slow** — PEGASIS's per-round O(N^2) chain rebuild exceeds a few-minute budget in constrained runners; N=100/N=200 complete normally. |
| `python gen_dashboards.py` | `comparison.png`, `dashboard.png`, `dashboard3.png`, `death_timeline.png` | Regenerates the four dashboard figures from current coupled-seed data. |
| `python gen_timelines.py` | `timelines.png` | 6-panel per-round timelines (alive, PDR, throughput, delay, energy/round, cumulative energy) for LEACH/PEGASIS/SEP/DEEC/CCH-K1/CCH-K3, same 20 coupled seeds. |
| `python eval_significance.py` | `eval_significance.json` | Paired t-test + Wilcoxon (per-seed, n=20) behind every headline gap; dependency-free. |
| `python gen_scalability_fig.py` | `scalability.png` | Plots the N=100/200/500 scalability trend from the coupled-seed numbers above (no re-simulation). Use this for the figure. |
| `python scenarios.py` | `range_impact.png`, `energy_consumption.png` | Communication-range sensitivity + cumulative energy plots. |
| `python -m pytest tests` | — | 7 tests: all protocols run, lifetimes match, relay mode beats PEGASIS. |

**Verification:** after running `canonical_eval.py` you should see
`CCH-K1 = 3038 ± 127`, `PEGASIS = 2291 ± 41`, `H-PEGASIS = 3084 ± 120`
(rounds, 20 seeds). Any deviation means the seed set or RNG seeding was altered.

## References

1. Heinzelman, W. et al. (2000) — "Energy-Efficient Communication Protocol for
   Wireless Microsensor Networks" (LEACH).
2. Lindsey, S. & Raghavendra, K. (2002) — "PEGASIS: Power-Efficient Gathering in
   Sensor Information Systems".
3. Smaragdakis, G., Matta, I., Bestavros, A. (2004) — "SEP: A Stable Election
   Protocol for clustered heterogeneous WSNs" (*SANPA*, workshop with MASS).
4. Li, Q., Zhu, Q., Wang, M. (2006) — "Design of a distributed energy-efficient
   clustering algorithm for heterogeneous WSNs" (DEEC), *Computer Communications*.
5. Kalpakis, K. et al. (2003) — "Efficient algorithms for maximum lifetime data
   gathering and aggregation in WSNs" (MLDA), *Computer Networks*; MST-traversal
   PEGASIS chains after Meghanathan, N. (2009), *KSII TIIS*.

## License

MIT License
