"""Experiment runner: LEACH vs PEGASIS comparison"""
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from leach import LEACH
from pegasis import PEGASIS


def run_experiment(n_nodes=100, max_rounds=2000, seed=42, n_runs=3):
    """Run multiple experiments with different seeds"""
    np.random.seed(seed)
    random_seeds = [seed + i * 100 for i in range(n_runs)]

    leach_histories = []
    pegasis_histories = []

    for run_idx, s in enumerate(random_seeds):
        print(f"\n=== Run {run_idx + 1}/{n_runs} (seed={s}) ===")

        # LEACH
        np.random.seed(s)
        leach = LEACH(n_nodes=n_nodes)
        leach_hist = leach.run(max_rounds)
        leach_histories.append(leach_hist)
        print(f"  LEACH: {len(leach_hist)} rounds, first node dead at round {leach_hist[0][0] if leach_hist else 'N/A'}")

        # PEGASIS
        np.random.seed(s)
        pegasis = PEGASIS(n_nodes=n_nodes)
        pegasis_hist = pegasis.run(max_rounds)
        pegasis_histories.append(pegasis_hist)
        print(f"  PEGASIS: {len(pegasis_hist)} rounds, first node dead at round {pegasis_hist[0][0] if pegasis_hist else 'N/A'}")

    return leach_histories, pegasis_histories


def aggregate_history(histories):
    """Average metrics across runs per round"""
    max_rounds = max(len(h) for h in histories)
    rounds = np.arange(1, max_rounds + 1)

    alive_mean = []
    energy_mean = []
    pdr_mean = []
    delay_mean = []
    throughput_mean = []
    loss_mean = []

    for r in range(max_rounds):
        alive_vals = [h[r][1] for h in histories if r < len(h)]
        energy_vals = [h[r][2] for h in histories if r < len(h)]
        pdr_vals = [h[r][3] for h in histories if r < len(h)]
        delay_vals = [h[r][4] for h in histories if r < len(h)]
        sent_vals = [h[r][5] for h in histories if r < len(h)]
        recv_vals = [h[r][6] for h in histories if r < len(h)]

        alive_mean.append(np.mean(alive_vals) if alive_vals else 0)
        energy_mean.append(np.mean(energy_vals) if energy_vals else 0)
        pdr_mean.append(np.mean(pdr_vals) if pdr_vals else 0)
        delay_mean.append(np.mean(delay_vals) if delay_vals else 0)
        total_sent = np.sum(sent_vals) if sent_vals else 0
        total_recv = np.sum(recv_vals) if recv_vals else 0
        throughput_mean.append(total_recv / max(1, total_sent))
        loss_mean.append(1 - total_recv / max(1, total_sent))

    return rounds, alive_mean, energy_mean, pdr_mean, delay_mean, throughput_mean, loss_mean


def plot_comparison(leach_histories, pegasis_histories, output_dir='.'):
    """Generate 6 comparison plots"""
    leach_rounds, leach_alive, leach_energy, leach_pdr, leach_delay, leach_throughput, leach_loss = aggregate_history(leach_histories)
    peg_rounds, peg_alive, peg_energy, peg_pdr, peg_delay, peg_throughput, peg_loss = aggregate_history(pegasis_histories)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle('LEACH vs PEGASIS Performance Comparison', fontsize=14, fontweight='bold')

    # 1. Network Lifetime (Alive Nodes)
    ax = axes[0, 0]
    ax.plot(leach_rounds, leach_alive, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_alive, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Alive Nodes')
    ax.set_title('Network Lifetime')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Energy Consumption per Round
    ax = axes[0, 1]
    ax.plot(leach_rounds, leach_energy, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_energy, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Energy (J/round)')
    ax.set_title('Energy Consumption per Round')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Packet Delivery Ratio
    ax = axes[0, 2]
    ax.plot(leach_rounds, leach_pdr, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_pdr, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('PDR')
    ax.set_title('Packet Delivery Ratio')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)

    # 4. Average Delay
    ax = axes[1, 0]
    ax.plot(leach_rounds, leach_delay, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_delay, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Delay (hops)')
    ax.set_title('Average End-to-End Delay')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 5. Throughput
    ax = axes[1, 1]
    ax.plot(leach_rounds, leach_throughput, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_throughput, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Throughput (pkts delivered / pkts sent)')
    ax.set_title('Throughput')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)

    # 6. Packet Loss
    ax = axes[1, 2]
    ax.plot(leach_rounds, leach_loss, 'b-', label='LEACH', linewidth=2)
    ax.plot(peg_rounds, peg_loss, 'r-', label='PEGASIS', linewidth=2)
    ax.set_xlabel('Round')
    ax.set_ylabel('Packet Loss Rate')
    ax.set_title('Packet Loss')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/comparison.png', dpi=150)
    plt.close()

    # Additional: First node death, half life, last node death
    def get_milestones(histories):
        first_death = []
        half_life = []
        last_death = []
        for h in histories:
            if h:
                first_death.append(h[0][0])
                half = next((r for r, a, *_ in h if a <= len(h[0]) / 2), h[-1][0])
                half_life.append(half)
                last_death.append(h[-1][0])
        return np.mean(first_death), np.mean(half_life), np.mean(last_death)

    leach_milestones = get_milestones(leach_histories)
    peg_milestones = get_milestones(pegasis_histories)

    print("\n=== MILESTONES (averaged over runs) ===")
    print(f"LEACH:    First death={leach_milestones[0]:.0f}, 50% dead={leach_milestones[1]:.0f}, Last death={leach_milestones[2]:.0f}")
    print(f"PEGASIS:  First death={peg_milestones[0]:.0f}, 50% dead={peg_milestones[1]:.0f}, Last death={peg_milestones[2]:.0f}")

    return leach_milestones, peg_milestones


def save_results(leach_histories, pegasis_histories, output_dir='.'):
    """Save raw data as JSON for report"""
    data = {
        'leach': [list(h) for h in leach_histories],
        'pegasis': [list(h) for h in pegasis_histories],
    }
    with open(f'{output_dir}/results.json', 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='LEACH vs PEGASIS Comparison')
    parser.add_argument('--nodes', type=int, default=100, help='Number of sensor nodes')
    parser.add_argument('--rounds', type=int, default=2000, help='Maximum rounds')
    parser.add_argument('--runs', type=int, default=3, help='Number of experiment runs')
    parser.add_argument('--seed', type=int, default=42, help='Base random seed')
    parser.add_argument('--output', type=str, default='.', help='Output directory')
    args = parser.parse_args()

    print(f"Running LEACH vs PEGASIS comparison")
    print(f"Nodes: {args.nodes}, Max rounds: {args.rounds}, Runs: {args.runs}")

    leach_histories, pegasis_histories = run_experiment(
        n_nodes=args.nodes,
        max_rounds=args.rounds,
        seed=args.seed,
        n_runs=args.runs
    )

    plot_comparison(leach_histories, pegasis_histories, args.output)
    save_results(leach_histories, pegasis_histories, args.output)

    print(f"\nResults saved to {args.output}/")
    print("  - comparison.png (4 plots)")
    print("  - results.json (raw data)")