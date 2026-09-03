"""Experiment runner: LEACH vs PEGASIS vs ClusterChain comparison.

ClusterChain is a hybrid routing protocol that combines LEACH-style clustering
with a PEGASIS-style greedy chain. The cluster-head set is chosen by residual
energy and proximity, and only the cluster heads (or, in dense mode, all nodes)
form the relay chain to the sink. The chain terminus that performs the single
expensive sink hop rotates by residual energy and proximity, avoiding PEGASIS's
blind round-robin leadership and keeping end-to-end delay low.
"""
import argparse
import json
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from leach import LEACH
from pegasis import PEGASIS
from clusterchain import ClusterChain


def run_experiment(n_nodes=100, max_rounds=2000, seed=42, n_runs=3):
    np.random.seed(seed)
    random_seeds = [seed + i * 100 for i in range(n_runs)]

    leach_histories, pegasis_histories, cc_histories = [], [], []

    for run_idx, s in enumerate(random_seeds):
        print(f"\n=== Run {run_idx + 1}/{n_runs} (seed={s}) ===")

        # Seed BOTH RNGs so every protocol sees the identical topology
        # (node positions use random.uniform; np.seed alone is not enough).
        random.seed(s)
        np.random.seed(s)
        leach = LEACH(n_nodes=n_nodes)
        leach_hist = leach.run(max_rounds)
        leach_histories.append(leach_hist)
        print(f"  LEACH: {len(leach_hist)} rounds")

        random.seed(s)
        np.random.seed(s)
        pegasis = PEGASIS(n_nodes=n_nodes)
        pegasis_hist = pegasis.run(max_rounds)
        pegasis_histories.append(pegasis_hist)
        print(f"  PEGASIS: {len(pegasis_hist)} rounds")

        random.seed(s)
        np.random.seed(s)
        cc = ClusterChain(n_nodes=n_nodes, ch_mode='dense', terminus='sink',
                          w_energy=0.7, n_ch=5, adaptive_k=False)
        cc_hist = cc.run(max_rounds)
        cc_histories.append(cc_hist)
        print(f"  ClusterChain: {len(cc_hist)} rounds")

    return leach_histories, pegasis_histories, cc_histories


def aggregate_history(histories, n_total):
    max_rounds = max(len(h) for h in histories)
    rounds = np.arange(1, max_rounds + 1)
    alive_mean, energy_mean, pdr_mean, delay_mean = [], [], [], []
    throughput_mean, loss_mean = [], []

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


def plot_comparison(leach_histories, pegasis_histories, cc_histories, output_dir='.'):
    lk = aggregate_history(leach_histories, 100)
    pg = aggregate_history(pegasis_histories, 100)
    cc = aggregate_history(cc_histories, 100)

    fig, axes = plt.subplots(2, 3, figsize=(17, 10))
    fig.suptitle('LEACH vs PEGASIS vs ClusterChain', fontsize=14, fontweight='bold')

    panels = [
        (0, 0, 'Network Lifetime', 'Alive Nodes', 'round', lk[1], pg[1], cc[1]),
        (0, 1, 'Energy per Round', 'Energy (J/round)', 'round', lk[2], pg[2], cc[2]),
        (0, 2, 'Packet Delivery Ratio', 'PDR', 'round', lk[3], pg[3], cc[3], (0, 1.05)),
        (1, 0, 'Average End-to-End Delay', 'Delay (hops)', 'round', lk[4], pg[4], cc[4]),
        (1, 1, 'Throughput', 'Throughput (delivered/sent)', 'round', lk[5], pg[5], cc[5], (0, 1.05)),
        (1, 2, 'Packet Loss', 'Loss Rate', 'round', lk[6], pg[6], cc[6], (0, 1.05)),
    ]
    for ax_r, ax_c, title, ylab, xlab, a, b, c, *ylim in panels:
        ax = axes[ax_r, ax_c]
        ax.plot(lk[0], a, 'b-', label='LEACH', linewidth=2)
        ax.plot(pg[0], b, 'r-', label='PEGASIS', linewidth=2)
        ax.plot(cc[0], c, 'g-', label='ClusterChain', linewidth=2)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        if ylim:
            ax.set_ylim(*ylim)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/comparison.png', dpi=150)
    plt.close()

    def get_milestones(histories, n_total):
        first, half, last = [], [], []
        for h in histories:
            if h:
                first.append(h[0][0])
                half.append(next((r for r, a, *_ in h if a <= n_total / 2), h[-1][0]))
                last.append(h[-1][0])
        return np.mean(first), np.mean(half), np.mean(last)

    lm = get_milestones(leach_histories, 100)
    pm = get_milestones(pegasis_histories, 100)
    cm = get_milestones(cc_histories, 100)

    print("\n=== MILESTONES (averaged over runs) ===")
    print(f"LEACH:       First={lm[0]:.0f}  50%dead={lm[1]:.0f}  Last={lm[2]:.0f}")
    print(f"PEGASIS:     First={pm[0]:.0f}  50%dead={pm[1]:.0f}  Last={pm[2]:.0f}")
    print(f"ClusterChain:First={cm[0]:.0f}  50%dead={cm[1]:.0f}  Last={cm[2]:.0f}")

    # ---- Dashboard ----
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['First death', '50% dead', 'Last death']
    x = np.arange(len(labels))
    w = 0.25
    ax.bar(x - w, [lm[0], lm[1], lm[2]], w, label='LEACH', color='#1f77b4')
    ax.bar(x, [pm[0], pm[1], pm[2]], w, label='PEGASIS', color='#d62728')
    ax.bar(x + w, [cm[0], cm[1], cm[2]], w, label='ClusterChain', color='#2ca02c')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Round')
    ax.set_title('Network Lifetime Milestones: LEACH vs PEGASIS vs ClusterChain')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    for i, (offset, vals) in enumerate([
        (-w, [lm[0], lm[1], lm[2]]),
        (0, [pm[0], pm[1], pm[2]]),
        (w, [cm[0], cm[1], cm[2]]),
    ]):
        for j, v in enumerate(vals):
            ax.text(x[j] + offset, float(v) + 5, f'{v:.0f}', ha='center', fontsize=8)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/dashboard.png', dpi=150)
    plt.close()

    return {'leach': lm, 'pegasis': pm, 'clusterchain': cm}


def save_results(leach_histories, pegasis_histories, cc_histories, output_dir='.'):
    data = {
        'leach': [list(h) for h in leach_histories],
        'pegasis': [list(h) for h in pegasis_histories],
        'clusterchain': [list(h) for h in cc_histories],
    }
    with open(f'{output_dir}/results.json', 'w') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='LEACH vs PEGASIS vs ClusterChain')
    parser.add_argument('--nodes', type=int, default=100)
    parser.add_argument('--rounds', type=int, default=2000)
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=str, default='.')
    args = parser.parse_args()

    lh, ph, ch = run_experiment(args.nodes, args.rounds, args.seed, args.runs)
    plot_comparison(lh, ph, ch, args.output)
    save_results(lh, ph, ch, args.output)
    print(f"\nResults saved to {args.output}/")
