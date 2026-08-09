# LEACH vs PEGASIS: WSN Routing Protocol Comparison

Simulation-based performance comparison of LEACH and PEGASIS hierarchical routing protocols for Wireless Sensor Networks.

## Overview

This project implements and compares two landmark WSN routing protocols:
- **LEACH** (Low-Energy Adaptive Clustering Hierarchy) — probabilistic cluster head rotation
- **PEGASIS** (Power-Efficient Gathering in Sensor Information Systems) — greedy chain formation

Both implemented in Python with a first-order radio energy model.

## Key Results

| Metric | LEACH | PEGASIS | Winner |
|--------|-------|---------|--------|
| Network Lifetime (50% dead) | 836 rounds | 1198 rounds | PEGASIS (+43%) |
| Packet Delivery Ratio | ~1.000 | ~0.010 | LEACH |
| Average Delay | 1.0 hops | ~100 hops | LEACH |
| Energy Efficiency | Lower | Higher | PEGASIS |

**PEGASIS achieves 1.44x longer network lifetime** at the cost of higher delay.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run comparison (3 runs, 2000 rounds each)
python run.py --nodes 100 --rounds 2000 --runs 3

# Outputs: comparison.png, dashboard.png, results.json
```

## Project Structure

```
.
├── energy.py       # First-order radio energy model
├── leach.py        # LEACH protocol implementation
├── pegasis.py      # PEGASIS protocol implementation
├── run.py          # Experiment runner with plotting
├── animate.py      # Protocol evolution animations (GIF)
├── visuals.py      # Additional visualizations
├── requirements.txt
└── comparison.png  # Generated: 6-panel comparison
```

## Simulation Parameters

- **Nodes**: 100, randomly deployed in 100m × 100m field
- **Sink**: Fixed at (50, 175)
- **Initial Energy**: 0.5 J per node
- **Packet Size**: 4000 bits
- **Energy Model**: First-order radio (Heinzelman et al., 2000)
- **Runs**: 3 independent seeds, up to 2000 rounds each

## Outputs

Running `python run.py` generates:
- `comparison.png` — 6-panel comparison (lifetime, energy, PDR, delay, throughput, loss)
- `dashboard.png` — Comprehensive dashboard with summary table
- `results.json` — Raw data for all runs

Additional visualizations available in `animate.py` and `visuals.py` (GIF animations, heatmaps, packet flow diagrams).

## Requirements

```
numpy<2
matplotlib>=3.7
```

## References

1. Heinzelman et al. (2000) — "Energy-Efficient Communication Protocol for Wireless Microsensor Networks"
2. Lindsey & Raghavendra (2002) — "PEGASIS: Power-Efficient Gathering in Sensor Information Systems"

## License

MIT License