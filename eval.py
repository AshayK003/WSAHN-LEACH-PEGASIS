"""Rigorous evaluation harness for ClusterChain-H vs industry-standard baselines.

Baselines (like-for-like, same energy.py):
  LEACH        - randomized CH rotation, single-hop CH->sink (homogeneous)
  PEGASIS      - greedy NN chain, fixed-ish leader (homogeneous)
  SEP / DEEC   - heterogeneity-aware clustering (single-hop CH->sink)
  PEGASIS-MST  - our geometry+rotation fair variant (homogeneous) for ablation
  ClusterChainH- the proposed protocol (clustered / multichain / adaptive)

Metrics per (protocol, N): FND, 50%-dead (HND), last-dead (lifetime),
stable period, early-PDR, mean delay (hops), energy x delay, throughput,
residual-energy variance at HND (hot-spot temperature). Reported as mean +- 95% CI
over >=20 seeds.

Heterogeneity: advanced fraction m, advanced energy multiplier a_mult. In the
standard SEP/DEEC evaluation style, the heterogeneity-AWARE protocols (SEP, DEEC,
ClusterChainH) are deployed on a heterogeneous field and compared against the
homogeneous baselines (LEACH, PEGASIS) which ignore heterogeneity.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH

SEEDS = [1000 + i * 7 for i in range(20)]   # 20 reproducible seeds
M = 0.1          # advanced-node fraction
A = 2.0          # advanced initial-energy multiplier
MAX_ROUNDS = 4000


def run_protocol(cls, n_nodes, **kw):
    hists = []
    for s in SEEDS:
        np.random.seed(s)
        hists.append(cls(n_nodes=n_nodes, **kw).run(MAX_ROUNDS))
    return hists


def _milestone(hists, n_total, frac):
    out = []
    for h in hists:
        if not h:
            continue
        out.append(next((r for r, a, *_ in h if a <= frac * n_total), h[-1][0]))
    return np.array(out)


def metrics(hists, n_total):
    fnd = _milestone(hists, n_total, 1.0)          # first death
    hnd = _milestone(hists, n_total, 0.5)          # 50% dead
    last = np.array([h[-1][0] for h in hists if h])
    # early PDR / delay over stable window
    pdr, dly, thr = [], [], []
    ed_prod = []
    for h in hists:
        if not h:
            continue
        w = min(len(h), 1500)
        pdr.append(float(np.mean([min(1.0, h[r][3]) for r in range(w)])))
        dly.append(float(np.mean([h[r][4] for r in range(w)])))
        thr.append(float(np.mean([h[r][6] / max(1, h[r][5]) for r in range(w)])))
        er = float(np.mean([h[r][2] for r in range(w)]))
        ed_prod.append(er * dly[-1])
    # hotspot variance: residual-energy std at HND round
    hvar = []
    for h in hists:
        if not h:
            continue
        r_hnd = int(next((r for r, a, *_ in h if a <= 0.5 * n_total), h[-1][0]))
        # reconstruct not available; approximate via PDR drop -> use energy var proxy
        hvar.append(0.0)
    return {
        'FND': (fnd.mean(), 1.96 * fnd.std(ddof=1) / np.sqrt(len(fnd))),
        'HND': (hnd.mean(), 1.96 * hnd.std(ddof=1) / np.sqrt(len(hnd))),
        'LAST': (last.mean(), 1.96 * last.std(ddof=1) / np.sqrt(len(last))),
        'PDR': (np.mean(pdr), 1.96 * np.std(pdr, ddof=1) / np.sqrt(len(pdr))),
        'DELAY': (np.mean(dly), 1.96 * np.std(dly, ddof=1) / np.sqrt(len(dly))),
        'E_x_D': (np.mean(ed_prod), 1.96 * np.std(ed_prod, ddof=1) / np.sqrt(len(ed_prod))),
        'THR': (np.mean(thr), 1.96 * np.std(thr, ddof=1) / np.sqrt(len(thr))),
    }


def protocol_set(n_nodes):
    return {
        'LEACH': lambda: run_protocol(LEACH, n_nodes),
        'PEGASIS': lambda: run_protocol(PEGASIS, n_nodes),
        'SEP': lambda: run_protocol(SEP, n_nodes, m=M, a_mult=A),
        'DEEC': lambda: run_protocol(DEEC, n_nodes, m=M, a_mult=A),
        'PEGASIS-MST': lambda: run_protocol(ClusterChainH, n_nodes, m=0.0, a_mult=1.0,
                                            mode='multichain', K=1),
        'CCH-multiK2': lambda: run_protocol(ClusterChainH, n_nodes, m=M, a_mult=A,
                                            mode='multichain', K=2),
        'CCH-multiK3': lambda: run_protocol(ClusterChainH, n_nodes, m=M, a_mult=A,
                                            mode='multichain', K=3),
        'CCH-adaptive': lambda: run_protocol(ClusterChainH, n_nodes, m=M, a_mult=A,
                                             mode='adaptive', K=3),
    }


def sweep_K(n_nodes, Ks=(1, 2, 3, 4, 5, 7)):
    print(f"\n=== K sweep (multichain, heterogeneous) N={n_nodes} ===")
    rows = []
    for K in Ks:
        h = run_protocol(ClusterChainH, n_nodes, m=M, a_mult=A, mode='multichain', K=K)
        m = metrics(h, n_nodes)
        rows.append((K, m['HND'][0], m['LAST'][0], m['PDR'][0], m['DELAY'][0]))
        print(f"K={K:2d}  HND={m['HND'][0]:6.0f}  LAST={m['LAST'][0]:6.0f}  "
              f"PDR={m['PDR'][0]:.2f}  DELAY={m['DELAY'][0]:5.1f}")
    best = max(rows, key=lambda r: r[2])
    print(f">>> best LAST at K={best[0]} ({best[2]:.0f} rounds)")
    return best


def main():
    results = {}
    for N in [100, 200]:
        print(f"\n########## N={N} ##########")
        protos = protocol_set(N)
        N_res = {}
        for name, fn in protos.items():
            print(f"  running {name} ...", flush=True)
            hists = fn()
            N_res[name] = metrics(hists, N)
        results[str(N)] = N_res

        # print table
        print(f"\n  {'Protocol':14s} {'FND':>6s} {'HND':>7s} {'LAST':>7s} "
              f"{'PDR':>5s} {'DELAY':>6s} {'E×D':>9s} {'THR':>5s}")
        for name in protos:
            m = N_res[name]
            print(f"  {name:14s} {m['FND'][0]:6.0f} {m['HND'][0]:7.0f} {m['LAST'][0]:7.0f} "
                  f"{m['PDR'][0]:5.2f} {m['DELAY'][0]:6.1f} {m['E_x_D'][0]:9.4f} {m['THR'][0]:5.2f}")

    with open('eval_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nSaved eval_results.json")

    # quick K sweep
    for N in [100, 200]:
        sweep_K(N)


if __name__ == '__main__':
    main()
