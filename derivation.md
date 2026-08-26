# Optimal Chain Length k* for ClusterChain

ClusterChain is a one-parameter family: **k** = number of relay nodes on the chain.
In clustered mode `k = n_ch` (5-7); in dense mode `k = N` (all nodes). This document
derives the energy-optimal k* from the Heinzelman first-order radio model and shows
how k trades delay against lifetime.

## Network model
- N = 100 nodes, uniform in a 100m x 100m field, sink at (50, 175).
- Distance from field centre to sink: D = 125 m. Crossover distance D0 = 87.7 m, so the
  sink hop is always **multipath** (E = E_mp * d^4).
- Energy: transmit `E_tx(d) = L(E_elec + E_amp d^2)` (free space, d < D0) or `L(E_elec + E_mp d^4)`
  (multipath); receive `E_rx = L E_elec`; aggregate `E_da = L * 5 nJ/bit`. L = 4000 bits.

## Per-round energy as a function of k
Every round, all N alive nodes sense and report one packet. The energy spent is:

1. **Member -> CH** (clustered mode only): (N-k) transmissions at free-space distance
   `d_m ~ M / (2 sqrt(pi k))`, so `d_m^2 ~ a^2/k`, `a = M/(2 sqrt(pi))`.
2. **CH receives** from members: N receives.
3. **Aggregation** at each CH: N packets fused.
4. **Chain relay**: (k-1) links at free-space distance `d_c ~ M/(2k)`, `d_c^2 ~ b^2/k^2`, `b = M/2`.
5. **Chain nodes receive** one relayed packet: k receives.
6. **Terminus -> sink**: one multipath hop at distance D (constant, does not depend on k).

```
E(k) = (N-k)[L E_elec + L E_fs (a^2/k)]           # member->CH
     + N (E_rx + E_da)                              # CH Rx + fusion
     + (k-1)[L E_elec + L E_fs (b^2/k^2)]           # chain relay
     + k E_rx                                       # chain Rx
     + L E_elec + L E_mp D^4                        # terminus->sink (constant)
```

## Where is the minimum?
The sink hop is constant, so k* is set by the balance between the two distance-squared
terms, both of which fall with k, and the fixed per-round overhead (Rx, DA) which
favours fewer nodes doing the relay work. Numerically minimising E(k) (see
`derive_kstar.py`) gives:

| Alive nodes N | k* (energy min) | E(k*) [J] | E(k=5) | E(k=7) | E(k=N) |
|---|---|---|---|---|---|
| 100 | 4 | 4.485e-2 | 4.489e-2 | 4.511e-2 | 6.327e-2 |
| 80  | 4 | 3.629e-2 | 3.636e-2 | 3.661e-2 | 5.087e-2 |
| 60  | 3 | 2.770e-2 | 2.784e-2 | 2.812e-2 | 3.847e-2 |
| 40  | 3 | 1.908e-2 | 1.931e-2 | 1.963e-2 | 2.607e-2 |
| 20  | 2 | 1.038e-2 | 1.078e-2 | 1.114e-2 | 1.367e-2 |

**k* stays small (2-4)** across the whole network lifetime. The model's per-round energy
is minimised by using few cluster heads and letting the multipath sink hop be shared.

## What the simulation shows (the honest caveat)
The empirical lifetime optimum is **k = N (dense mode, 1162 rounds)**, *not* k*=4.
The simple E(k) model above misses a second-order effect: with few cluster heads, the
heads and the rotation terminus bear disproportionate relay + fusion load and die early,
shortening lifetime. PEGASIS's dense chain spreads that load across all nodes. So:

- **k* from the energy model = the delay-favoring design point** (5-7 heads -> 5-7 hop
  delay, 15x lower than PEGASIS, ~5% lifetime cost).
- **k = N = the lifetime-favoring design point** (matches PEGASIS, ~100-hop delay).

The chain length k is therefore the single knob that trades delay against lifetime,
and ClusterChain makes that tradeoff explicit and tunable rather than hidden. This is
the principled contribution: a *unification* of the LEACH (k->1, single cluster) and
PEGASIS (k=N, full chain) design spaces under one analytically-grounded parameter.

## Reproduce
```
python derive_kstar.py    # prints k* table + writes kstar_result.txt
```
