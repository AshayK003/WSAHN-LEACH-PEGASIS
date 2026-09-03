"""Paired significance tests behind the headline lifetime claims (REPORT 9.6).

Re-runs the canonical N=100 heterogeneous set (20 coupled seeds, both RNGs
seeded) and stores PER-SEED LAST/PDR/DELAY, then tests CCH-K1 against every
baseline on paired per-seed differences:

  * paired Student t-test (exact p via the regularised incomplete beta —
    dependency-free, no scipy needed);
  * Wilcoxon signed-rank test (normal approximation with continuity + tie
    correction — standard for n >= 10).

H0: mean/median paired difference (CCH-K1 minus baseline) is zero.
A gap is claimed only if BOTH tests reject at alpha = 0.05.

Saves eval_significance.json. Run: python eval_significance.py (a few minutes)
"""
import json
import math
import random
import numpy as np

from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from recent_variants import DualHead, PSOCH
from hpegasis import HPEGASIS
from clusterchain_h import ClusterChainH

M, A, N, MAXR = 0.1, 2.0, 100, 6000
SEEDS = [1000 + i * 7 for i in range(20)]
W = 1500  # stable window for PDR/DELAY (same as canonical_eval.py)

PROTOCOLS = {
    'LEACH': (LEACH, dict(m=M, a_mult=A)),
    'PEGASIS': (PEGASIS, dict(m=M, a_mult=A)),
    'SEP': (SEP, dict(m=M, a_mult=A)),
    'DEEC': (DEEC, dict(m=M, a_mult=A)),
    'DCK-LEACH': (DualHead, dict(m=M, a_mult=A, K=5)),
    'NPSOP': (PSOCH, dict(m=M, a_mult=A, K=5)),
    'H-PEGASIS': (HPEGASIS, dict(m=M, a_mult=A)),
    'CCH-K1': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=1)),
    'CCH-K2': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=2)),
    'CCH-K3': (ClusterChainH, dict(m=M, a_mult=A, mode='multichain', K=3)),
}


# ---------------- exact paired t-test (no scipy) ----------------
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delt = c * d
        h *= delt
        if abs(delt - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def paired_ttest(x, y):
    """Paired t-test on per-seed samples. Returns (t_stat, two-sided p)."""
    d = np.asarray(x, float) - np.asarray(y, float)
    n = len(d)
    md, sd = float(d.mean()), float(d.std(ddof=1))
    if sd == 0:
        return 0.0, 1.0 if md == 0 else 0.0
    t = md / (sd / math.sqrt(n))
    nu = n - 1
    p = _betai(nu / 2.0, 0.5, nu / (nu + t * t))
    return t, min(1.0, max(0.0, p))


def wilcoxon_signed_rank(x, y):
    """Wilcoxon signed-rank, normal approx. with continuity + tie correction.
    Returns (W_plus, z, two-sided p)."""
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 0.0, 0.0, 1.0
    ad = np.abs(d)
    # average ranks with tie handling
    order = np.argsort(ad, kind='stable')
    avg_ranks = np.empty(n)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ad[order[j + 1]] == ad[order[i]]:
            j += 1
        avg_ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    w = float(avg_ranks[d > 0].sum())
    mu = n * (n + 1) / 4.0
    _, counts = np.unique(ad, return_counts=True)
    tie = float(np.sum(counts ** 3 - counts))
    var = n * (n + 1) * (2 * n + 1) / 24.0 - tie / 48.0
    if var <= 0:
        return w, 0.0, 1.0
    z = (w - mu - 0.5 * math.copysign(1, w - mu)) / math.sqrt(var)
    p = math.erfc(abs(z) / math.sqrt(2))
    return w, z, min(1.0, max(0.0, p))


def ci_diff(x, y):
    d = np.asarray(x, float) - np.asarray(y, float)
    m = float(d.mean())
    h = float(1.96 * d.std(ddof=1) / math.sqrt(len(d)))
    return m, h


def main():
    print("Running canonical set for per-seed significance data...")
    per_seed = {}
    for name, (cls, kw) in PROTOCOLS.items():
        lasts, pdrs, dlys = [], [], []
        for s in SEEDS:
            random.seed(s)
            np.random.seed(s)
            h = cls(n_nodes=N, **kw).run(MAXR)
            lasts.append(h[-1][0])
            c = min(len(h), W)
            pdrs.append(float(np.mean([min(1.0, h[r][3]) for r in range(c)])))
            dlys.append(float(np.mean([h[r][4] for r in range(c)])))
        per_seed[name] = {'LAST': lasts, 'PDR': pdrs, 'DELAY': dlys}
        print(f"  {name:12s} LAST={np.mean(lasts):7.0f}")

    base = per_seed['CCH-K1']['LAST']
    tests = {}
    rows = []
    for name in PROTOCOLS:
        if name == 'CCH-K1':
            continue
        other = per_seed[name]['LAST']
        md, hd = ci_diff(base, other)
        t, pt = paired_ttest(base, other)
        w, z, pw = wilcoxon_signed_rank(base, other)
        wins = int(np.sum(np.asarray(base) > np.asarray(other)))
        tests[name] = {'mean_diff': md, 'ci95': hd, 't': t, 'p_t': pt,
                       'W': w, 'z': z, 'p_w': pw, 'wins': wins, 'n': len(base),
                       'sig_both': bool(pt < 0.05 and pw < 0.05)}
        rows.append((name, md, hd, t, pt, pw, wins))

    with open('eval_significance.json', 'w') as f:
        json.dump({'per_seed_LAST': {k: v['LAST'] for k, v in per_seed.items()},
                   'tests_vs_CCH-K1': tests}, f, indent=2)

    print(f"\n{'baseline':12s} {'meanΔ':>7s} {'±95%':>6s} {'t':>7s} "
          f"{'p(t)':>9s} {'p(W)':>9s} {'wins':>7s} sig")
    for name, md, hd, t, pt, pw, wins in rows:
        sig = 'YES' if (pt < 0.05 and pw < 0.05) else 'no'
        print(f"{name:12s} {md:7.0f} {hd:6.0f} {t:7.2f} {pt:9.2e} {pw:9.2e} "
              f"{wins:2d}/20  {sig}")
    print("Saved eval_significance.json")


if __name__ == '__main__':
    main()
