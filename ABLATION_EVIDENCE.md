# Negative-Result Evidence: Mechanism Ablations vs ClusterChain-H Baseline

These files document a controlled A/B test of two mechanisms suggested by a
2021-2026 WSN routing literature review, run against the current
ClusterChain-H multichain K=1 design under the project's fixed benchmark.

## Benchmark (identical for every protocol)
- 100 nodes, 100x100 m field, sink at (50, 175)
- First-order radio model (Heinzelman et al.)
- 0.5 J normal / 1.0 J advanced nodes (10% at 2x), 4000-bit packets
- 20 seeds; BOTH `random` and `numpy` seeded per seed so every protocol
  sees the identical node topology (like-for-like, not just in expectation)
- Metrics: FND / LAST / PDR / hop delay / Energy x Delay, plus per-class
  first-death (normal vs advanced) for the instrumented variants.

## Files
- `cch_experimental.py`   : experimental protocol subclass (energy-gradient
                            relay, adaptive-K, selective dual-terminus
                            fail-over). Reuses ClusterChainH transmission
                            logic + energy.py; only chain build / K selection
                            / vice fail-over are changed.
- `eval_experimental.py`  : A/B of energy-gradient relay + adaptive-K.
- `eval_dualterminus.py`  : A/B of selective dual-terminus (+ per-class curves).
- `eval_experimental.json`: results (run with coupled seeding).
- `eval_dualterminus.json`: results (run with coupled seeding).
- `cch_localrepair.py`     : ClusterChainH subclass with AODV-style local
                            chain repair (splice single dead node out of the
                            cached order, O(|chain|), instead of a full
                            greedy + 2-opt / MST rebuild). Falls back to the
                            baseline rebuild for multi-node changes.
- `eval_localrepair.py`     : 3-seed hypothesis test (H1/H2/H3 gates).
- `eval_lr_canonical.py`    : 20-seed canonical (N=100) + 3-seed scaling
                            (N=500) verdict.
- `eval_localrepair.json`, `eval_lr_canonical.json`: results.
- `tests/test_localrepair.py`: 6 fast unit tests (splice positions,
                            fallback cases, pre-death trajectory identity).

## Reproduce
    python eval_experimental.py
    python eval_dualterminus.py
    python eval_localrepair.py
    python -u eval_lr_canonical.py

## Results (mean LAST, xPEG = ratio vs CCH-K1)
| protocol                     |   LAST | xPEG  |
|------------------------------|--------|-------|
| CCH-K1 (baseline)            | 3038   | 1.00  |
| CCH-K3 (delay reference)     | 2819   | 0.93  |
| EG-K1 (energy-gradient relay)| 2480  | 0.82  |
| EG-ADP (relay + adaptive-K)  | 2233   | 0.73  |
| DT-K1 (selective dual-term)  | 3055   | 1.01  |
| DT-K3 (dual-term, K=3)       | 2815   | 0.93  |
| LR-K1 (local chain repair)   | 2903   | 0.96  |

## Conclusion
Neither literature-prescribed mechanism beats the existing MST-geometry
multichain K=1 design:
- Energy-gradient relay spreads load (FND rises 493 -> 986/1238) but raises
  total per-round radio cost, collapsing the whole network sooner (0.73-0.82x).
- Selective dual-terminus fail-over is statistically indistinguishable from
  baseline (1.01x); the vice node is depleted by end-of-life so the fail-over
  rarely fires.
- Local chain repair replaces 99% of rebuilds and runs 7.4x faster at N=500,
  but spliced chains skip re-optimization and the tail dies earlier (0.96x,
  FND unchanged at 493). Kept as an eval accelerator, not a protocol change.
Per-class curves confirm heterogeneity works as intended: in DT-K1, normal
nodes die at round ~356 while advanced nodes survive to ~1113.
