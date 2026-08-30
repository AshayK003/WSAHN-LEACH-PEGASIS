"""Final evaluation: ClusterChain-H vs baselines, with homogeneous ablation and
scalability. Produces eval_full.json, lifetime.png, scalability.png."""
import json
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH
from recent_variants import DualHead, PSOCH

M, A = 0.1, 2.0
MAX_ROUNDS = 6000


def run(cls, n_nodes, seeds, **kw):
    out = []
    for s in seeds:
        random.seed(s)
        np.random.seed(s)
        out.append(cls(n_nodes=n_nodes, **kw).run(MAX_ROUNDS))
    return out


def milestone(hists, n_total, frac):
    # frac=1.0 means "last node dead" -> use the final round of each history,
    # not the first round where alive<=n_total (which is always round 0).
    if frac >= 1.0:
        return np.array([h[-1][0] for h in hists if h])
    return np.array([next((r for r, a, *_ in h if a <= frac * n_total), h[-1][0])
                     for h in hists if h])


def metrics(hists, n_total):
    fnd = milestone(hists, n_total, 1.0)
    hnd = milestone(hists, n_total, 0.5)
    last = np.array([h[-1][0] for h in hists if h])
    pdr, dly, ed = [], [], []
    for h in hists:
        if not h:
            continue
        w = min(len(h), 1500)
        pdr.append(float(np.mean([min(1.0, h[r][3]) for r in range(w)])))
        d = float(np.mean([h[r][4] for r in range(w)]))
        dly.append(d)
        er = float(np.mean([h[r][2] for r in range(w)]))
        ed.append(er * d)
    return {
        'FND': (fnd.mean(), 1.96 * fnd.std(ddof=1) / np.sqrt(len(fnd))),
        'HND': (hnd.mean(), 1.96 * hnd.std(ddof=1) / np.sqrt(len(hnd))),
        'LAST': (last.mean(), 1.96 * last.std(ddof=1) / np.sqrt(len(last))),
        'PDR': (np.mean(pdr), 1.96 * np.std(pdr, ddof=1) / np.sqrt(len(pdr))),
        'DELAY': (np.mean(dly), 1.96 * np.std(dly, ddof=1) / np.sqrt(len(dly))),
        'E_x_D': (np.mean(ed), 1.96 * np.std(ed, ddof=1) / np.sqrt(len(ed))),
    }


SEEDS100 = [1000 + i * 7 for i in range(20)]
SEEDS200 = [2000 + i * 11 for i in range(12)]
SEEDS500 = [3000 + i * 13 for i in range(8)]


def protos_hetero(n, seeds):
    return {
        'LEACH': run(LEACH, n, seeds),
        'PEGASIS': run(PEGASIS, n, seeds),
        'SEP': run(SEP, n, seeds, m=M, a_mult=A),
        'DEEC': run(DEEC, n, seeds, m=M, a_mult=A),
        'DCK-LEACH22': run(DualHead, n, seeds, m=M, a_mult=A, K=5),
        'NPSOP23': run(PSOCH, n, seeds, m=M, a_mult=A, K=5),
        'CCH-K1': run(ClusterChainH, n, seeds, m=M, a_mult=A, mode='multichain', K=1),
        'CCH-K2': run(ClusterChainH, n, seeds, m=M, a_mult=A, mode='multichain', K=2),
        'CCH-K3': run(ClusterChainH, n, seeds, m=M, a_mult=A, mode='multichain', K=3),
    }


def main():
    results = {}
    # N=100 heterogeneous (20 seeds)
    print("N=100 heterogeneous ...")
    r100 = {k: metrics(v, 100) for k, v in protos_hetero(100, SEEDS100).items()}
    results['100'] = r100
    # homogeneous ablation N=100 (CCH vs PEGASIS)
    pg_h = run(PEGASIS, 100, SEEDS100)
    cch_h = run(ClusterChainH, 100, SEEDS100, m=0.0, a_mult=1.0, mode='multichain', K=1)
    results['100_homogeneous'] = {
        'PEGASIS': metrics(pg_h, 100),
        'CCH(K=1)': metrics(cch_h, 100),
    }
    # scalability
    for n, seeds in [(200, SEEDS200), (500, SEEDS500)]:
        print(f"N={n} ...")
        results[str(n)] = {k: metrics(v, n) for k, v in protos_hetero(n, seeds).items()}

    with open('eval_full.json', 'w') as f:
        json.dump(results, f, indent=2)

    # ---- console tables ----
    for n in ['100', '200', '500']:
        print(f"\n===== N={n} (heterogeneous) =====")
        print(f"{'Protocol':14s} {'FND':>6s} {'HND':>7s} {'LAST':>7s} {'PDR':>5s} "
              f"{'DELAY':>6s} {'E×D':>9s}")
        for k, m in results[n].items():
            print(f"{k:14s} {m['FND'][0]:6.0f} {m['HND'][0]:7.0f} {m['LAST'][0]:7.0f} "
                  f"{m['PDR'][0]:5.2f} {m['DELAY'][0]:6.1f} {m['E_x_D'][0]:9.4f}")
    print("\n===== N=100 homogeneous (geometry-only ablation) =====")
    for k, m in results['100_homogeneous'].items():
        print(f"{k:14s} LAST={m['LAST'][0]:.0f}  PDR={m['PDR'][0]:.2f}  "
              f"DELAY={m['DELAY'][0]:.1f}")

    # ---- figure 1: lifetime bars N=100 ----
    order = ['LEACH', 'PEGASIS', 'DEEC', 'SEP', 'DCK-LEACH22', 'NPSOP23',
             'CCH-K1', 'CCH-K2', 'CCH-K3']
    colors = ['#d62728' if k.startswith('CCH') else '#2ca02c' for k in order]
    means = [results['100'][k]['LAST'][0] for k in order]
    errs = [results['100'][k]['LAST'][1] for k in order]
    plt.figure(figsize=(11, 5))
    plt.bar(order, means, yerr=errs, capsize=4, color=colors)
    plt.ylabel('Network lifetime (rounds, last node dead)')
    plt.title('N=100 heterogeneous: Network Lifetime (mean ± 95% CI, 20 seeds)')
    plt.xticks(rotation=25, ha='right')
    for i, v in enumerate(means):
        plt.text(i, v, f'{v:.0f}', ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    plt.savefig('lifetime.png', dpi=150)
    plt.close()

    # ---- figure 2: scalability (LAST vs N) ----
    ns = [100, 200, 500]
    key = 'CCH-K3'
    base = 'PEGASIS'
    cch = [results[str(n)][key]['LAST'][0] for n in ns]
    peg = [results[str(n)][base]['LAST'][0] for n in ns]
    plt.figure(figsize=(8, 5))
    plt.plot(ns, cch, 'o-', label='CCH-K3', color='#2ca02c')
    plt.plot(ns, peg, 's-', label='PEGASIS', color='#d62728')
    plt.xlabel('Number of nodes N')
    plt.ylabel('Network lifetime (rounds)')
    plt.title('Scalability: CCH-K3 vs PEGASIS')
    plt.legend(); plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('scalability.png', dpi=150)
    plt.close()
    print("\nSaved eval_full.json, lifetime.png, scalability.png")


if __name__ == '__main__':
    main()
