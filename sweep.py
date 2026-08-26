"""Parameter sweep for ClusterChain.

Finds the configuration that maximises network lifetime (50% / 100% node death)
while keeping PDR high and delay low, across three cluster-head selection
strategies: 'sink', 'spread', 'coverage'.
"""
import numpy as np
from leach import LEACH
from pegasis import PEGASIS
from clusterchain import ClusterChain

N_NODES = 100


def milestones(histories, n_total=N_NODES):
    first, half, last = [], [], []
    for h in histories:
        if not h:
            continue
        first.append(h[0][0])
        half.append(next((r for r, a, *_ in h if a <= n_total / 2), h[-1][0]))
        last.append(h[-1][0])
    return (np.mean(first) if first else 0,
            np.mean(half) if half else 0,
            np.mean(last) if last else 0)


def run_protocol(cls, **kwargs):
    hists = []
    for s in [42, 142, 242]:
        np.random.seed(s)
        hists.append(cls(n_nodes=N_NODES, **kwargs).run(2000))
    return hists


def main():
    print("Baselines (n=100, 3 seeds)...")
    leach = run_protocol(LEACH)
    peg = run_protocol(PEGASIS)
    lm, pm = milestones(leach), milestones(peg)
    print(f"  LEACH   50%dead={lm[1]:.0f}  last={lm[2]:.0f}")
    print(f"  PEGASIS 50%dead={pm[1]:.0f}  last={pm[2]:.0f}")

    rows = []
    for mode in ['sink', 'spread', 'coverage', 'dense']:
        for n_ch in [3, 4, 5, 6, 7]:
            for w in [0.5, 0.7, 0.9]:
                for term in ['energy', 'sink']:
                    hists = run_protocol(ClusterChain, n_ch=n_ch, w_energy=w,
                                         ch_mode=mode, terminus=term)
                    m = milestones(hists)
                    pdr_early = np.mean([
                        np.mean([min(1.0, h[r][3]) for r in range(min(800, len(h)))])
                        for h in hists
                    ])
                    avg_delay = np.mean([
                        np.mean([h[r][4] for r in range(min(800, len(h)))])
                        for h in hists
                    ])
                    rows.append((mode, n_ch, w, term, m[1], m[2], pdr_early, avg_delay))

    print(f"\n{'mode':>7} {'n_ch':>4} {'w':>4} {'term':>5} {'50%dead':>8} {'last':>7} {'PDR@800':>9} {'delay@800':>10}")
    rows.sort(key=lambda x: (-x[4], -x[6], x[7]))
    for mode, n_ch, w, term, half, last, pdr, dly in rows[:15]:
        print(f"{mode:>7} {n_ch:>4} {w:>4.1f} {term:>5} {half:>8.0f} {last:>7.0f} {pdr:>9.3f} {dly:>10.2f}")

    best = rows[0]
    print(f"\nBEST by 50%dead (PDR, delay tiebreak): mode={best[0]} n_ch={best[1]} w={best[2]:.1f} term={best[3]}")
    print(f"  50%dead={best[4]:.0f}  last={best[5]:.0f}  PDR={best[6]:.3f}  delay={best[7]:.2f}")
    print(f"  vs PEGASIS: 50%dead {best[4]/pm[1]:.2f}x, last {best[5]/pm[2]:.2f}x")
    print(f"  vs LEACH:   50%dead {best[4]/lm[1]:.2f}x, last {best[5]/lm[2]:.2f}x")


if __name__ == '__main__':
    main()
