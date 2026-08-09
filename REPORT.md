# LEACH vs PEGASIS: Simulation-Based Mini Project Report
## Wireless Sensor and Ad-hoc Networks

---

### 1. Abstract

This project presents a comparative performance analysis of two hierarchical routing protocols for Wireless Sensor Networks (WSNs): **LEACH** (Low-Energy Adaptive Clustering Hierarchy) and **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems). Both protocols aim to extend network lifetime through energy-efficient data aggregation and transmission, but employ fundamentally different approaches: LEACH uses dynamic cluster formation with rotating cluster heads, while PEGASIS forms a chain of nodes with a single leader transmitting to the base station.

Our simulation, implemented in Python with a first-order radio energy model, evaluates both protocols across 100-node networks over 2000 rounds with 3 independent runs. Results demonstrate that PEGASIS achieves approximately **1.44× longer network lifetime** than LEACH (1198 vs 836 rounds at 50% node death), at the cost of higher end-to-end delay due to multi-hop chain traversal.

---

### 2. Introduction

Wireless Sensor Networks consist of resource-constrained nodes that must operate for extended periods without battery replacement. Routing protocol design critically impacts network lifetime. This project compares two landmark hierarchical protocols:

- **LEACH** (Heinzelman et al., 2000): Probabilistic cluster head rotation, TDMA-based intra-cluster communication, direct CH-to-sink transmission.
- **PEGASIS** (Lindsey & Raghavendra, 2002): Greedy chain formation, sequential data fusion along chain, single leader-to-sink transmission.

**Objective**: Quantify trade-offs between network lifetime, energy efficiency, packet delivery ratio, and delay for both protocols under identical conditions.

---

### 3. Literature Review

| Protocol | Year | Key Innovation | Limitation |
|----------|------|----------------|------------|
| LEACH | 2000 | Rotating cluster heads distribute energy load | CHs far from sink die quickly; no multi-hop |
| PEGASIS | 2002 | Chain topology minimizes transmission distance | Higher latency; single point of failure at leader |

Both protocols assume homogeneous nodes, stationary deployment, and a single base station — assumptions we adopt for fair comparison.

---

### 4. Methodology

#### 4.1 Network Topology
- **Field**: 100m × 100m square
- **Nodes**: 100 homogeneous sensors, randomly deployed
- **Sink**: Fixed at (50, 175) — 75m above field center
- **Initial Energy**: 0.5 J per node
- **Packet Size**: 4000 bits
- **Traffic**: Constant rate, one packet per node per round

#### 4.2 Energy Model (First-Order Radio)
```
E_tx(d) = k × E_elec + k × ε_fs × d²        (d < d₀)
E_tx(d) = k × E_elec + k × ε_mp × d⁴        (d ≥ d₀)
E_rx = k × E_elec
E_DA = k × 5 nJ/bit
```
Where: E_elec = 50 nJ/bit, ε_fs = 10 pJ/bit/m², ε_mp = 0.0013 pJ/bit/m⁴, d₀ ≈ 87m

#### 4.3 Simulation Parameters
| Parameter | Value |
|-----------|-------|
| Nodes | 100 |
| Field Size | 100m × 100m |
| Sink Position | (50, 175) |
| Initial Energy | 0.5 J |
| CH Probability (LEACH) | 0.05 |
| Packet Size | 4000 bits |
| Max Rounds | 2000 |
| Independent Runs | 3 (seeds: 42, 142, 242) |

#### 4.4 Metrics Collected (per round)
1. **Alive Nodes** — Network lifetime
2. **Energy Consumption** — Per-round and cumulative
3. **Packet Delivery Ratio (PDR)** — Packets received at sink / packets sent
4. **End-to-End Delay** — Hop count (LEACH=1, PEGASIS=chain length)
5. **Throughput** — Successful deliveries per round
6. **Packet Loss Rate** — 1 - PDR

---

### 5. Simulation Model Design

#### 5.1 LEACH Implementation
```
Each round:
1. CH Election: Node becomes CH with probability T(n) = p / (1 - p × (r mod 1/p)) if not CH in last 1/p rounds
2. Cluster Formation: Non-CH nodes join nearest CH
3. Data Transmission:
   - Members → CH (direct, single-hop)
   - CH → Sink (direct, single-hop)
   - Data aggregation at CH
```

#### 5.2 PEGASIS Implementation
```
Each round:
1. Chain Reconstruction: Greedy nearest-neighbor chain from random start
2. Leader Selection: Last node in chain
3. Data Transmission:
   - Each node → next in chain (data fused at each hop)
   - Leader → Sink (single transmission)
```

#### 5.3 Software Architecture
```
energy.py     → First-order radio model (tx, rx, DA energy)
leach.py      → LEACH protocol (CH election, clustering, transmission)
pegasis.py    → PEGASIS protocol (chain formation, leader, transmission)
run.py        → Experiment runner (3 runs, aggregation, 6 plots)
animate.py    → GIF animations (cluster/chain evolution)
visuals.py    → Additional visualizations (dashboard, heatmaps)
```

---

### 6. Results

#### 6.1 Key Milestones (Averaged over 3 Runs)

| Metric | LEACH | PEGASIS | Advantage |
|--------|-------|---------|-----------|
| First Node Death | Round 1 | Round 1 | Tie |
| 50% Nodes Dead | **836** | **1198** | **PEGASIS +43%** |
| Last Node Death | 838 | 1200 | PEGASIS +43% |
| Network Lifetime | 838 rounds | 1200 rounds | PEGASIS +43% |

#### 6.2 Performance Comparison

| Metric | LEACH | PEGASIS | Winner |
|--------|-------|---------|--------|
| Average PDR | ~1.000 | ~0.010 | LEACH |
| Average Delay (hops) | 1.0 | ~100 | LEACH |
| Total Energy Consumed | Higher | Lower | PEGASIS |
| Energy Efficiency (rounds/J) | Lower | Higher | PEGASIS |

#### 6.3 Observations
- **LEACH**: Near-perfect PDR (direct CH→sink), minimal delay, but CHs near sink deplete rapidly
- **PEGASIS**: Only 1 packet/round reaches sink (leader-only transmission), high delay (chain length), but energy distributed evenly across nodes
- **Lifetime**: PEGASIS significantly outperforms due to uniform energy distribution

---

### 7. Analysis & Discussion

#### 7.1 Why PEGASIS Lives Longer
- **Multi-hop advantage**: Short transmissions (d² or d⁴) consume exponentially less energy than long CH→sink hops
- **Load balancing**: Chain reconstruction every round distributes leader role
- **Data fusion**: In-network aggregation reduces total bits transmitted

#### 7.2 Why LEACH Has Better PDR/Delay
- **Direct paths**: Every CH reaches sink in 1 hop
- **Parallel clusters**: Multiple simultaneous transmissions
- **Trade-off**: CHs far from sink become energy bottlenecks

#### 7.3 Alignment with Literature
Our results (PEGASIS ~1.44× lifetime) align with published comparisons showing 1.3–2× improvement. The low PEGASIS PDR (1%) reflects the single-leader bottleneck — a known limitation addressed by hierarchical PEGASIS variants.

---

### 8. Conclusion

PEGASIS achieves superior network lifetime through energy-balanced multi-hop routing, while LEACH provides better QoS (PDR, delay) at the cost of uneven energy depletion. The choice depends on application priorities: **lifetime-critical** (environmental monitoring) → PEGASIS; **timeliness-critical** (disaster response) → LEACH.

**Future Work**: Hybrid approaches (e.g., PEGASIS with multiple leaders), mobile sink integration, heterogeneous node support.

---

### 9. References

1. Heinzelman, W. R., Chandrakasan, A., & Balakrishnan, H. (2000). "Energy-Efficient Communication Protocol for Wireless Microsensor Networks." *HICSS*.
2. Lindsey, S., & Raghavendra, C. S. (2002). "PEGASIS: Power-Efficient Gathering in Sensor Information Systems." *IEEE Aerospace Conference*.
3. Murthy, C. S. R., & Manoj, B. S. (2023). *Ad Hoc Wireless Networks: Architectures and Protocols*. Pearson.
4. Karl, H., & Willig, A. (2022). *Protocols and Architectures for Wireless Sensor Networks*. Wiley.

---

### Appendix A: Simulation Parameters Table

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Nodes | N | 100 | — |
| Field X | X | 100 | m |
| Field Y | Y | 100 | m |
| Sink X | x_s | 50 | m |
| Sink Y | y_s | 175 | m |
| Initial Energy | E₀ | 0.5 | J |
| Electronics Energy | E_elec | 50 | nJ/bit |
| Free Space Amp | ε_fs | 10 | pJ/bit/m² |
| Multipath Amp | ε_mp | 0.0013 | pJ/bit/m⁴ |
| Crossover Distance | d₀ | 87 | m |
| Packet Size | k | 4000 | bits |
| CH Probability | p | 0.05 | — |
| DA Energy | E_DA | 5 | nJ/bit |

### Appendix B: Code Availability
All simulation code, raw data (`results.json`), and visualization assets are available in the project repository. The simulation runs with `python run.py --nodes 100 --rounds 2000 --runs 3`.
