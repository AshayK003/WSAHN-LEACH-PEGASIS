import json
import numpy as np
from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH, optimal_k
from recent_variants import DualHead, PSOCH
from hpegasis import HPEGASIS

M, A = 0.1, 2.0
MAX_ROUNDS = 6000
SEEDS = [1000 + i * 7 for i in range(20)]


def run(cls, n, seeds, **kw):
    out = []
    for s in seeds:
        # Seed BOTH RNGs so every protocol sees the identical node topology
        # for a given seed (ClusterChainH.__init__ draws positions via
        # random.uniform). Without random.seed the LAST values are not
        # reproducible from seeds alone.
        import random as _r
        _r.seed(s)
        np.random.seed(s)
        out.append(cls(n_nodes=n, **kw).run(MAX_ROUNDS))
    return out


def ci(arr):
    arr = np.asarray(arr, float)
    return float(arr.mean()), float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr)))


# ALL protocols under ONE identical heterogeneous deployment (m=0.1, a_mult=2.0)
protos = {
    'LEACH': run(LEACH, 100, SEEDS, m=M, a_mult=A),
    'PEGASIS': run(PEGASIS, 100, SEEDS, m=M, a_mult=A),
    'DEEC': run(DEEC, 100, SEEDS, m=M, a_mult=A),
    'SEP': run(SEP, 100, SEEDS, m=M, a_mult=A),
    'DCK-LEACH22': run(DualHead, 100, SEEDS, m=M, a_mult=A, K=5),
    'NPSOP23': run(PSOCH, 100, SEEDS, m=M, a_mult=A, K=5),
    'CCH-K1': run(ClusterChainH, 100, SEEDS, m=M, a_mult=A, mode='multichain', K=1),
    'CCH-K2': run(ClusterChainH, 100, SEEDS, m=M, a_mult=A, mode='multichain', K=2),
    'CCH-K3': run(ClusterChainH, 100, SEEDS, m=M, a_mult=A, mode='multichain', K=3),
    'CCH-ADP': run(ClusterChainH, 100, SEEDS, m=M, a_mult=A, mode='adaptive', K=5),
    'CCH-CLUSTK1': run(ClusterChainH, 100, SEEDS, m=M, a_mult=A, mode='clustered', K=1,
                       adaptive_k=False),
    'H-PEGASIS': run(HPEGASIS, 100, SEEDS, m=M, a_mult=A),
}
print('optimal_k used by clustered mode: n=100 ->', optimal_k(100, 1),
      ', n=50 ->', optimal_k(50, 1))

result = {}
for k, hists in protos.items():
    last = [h[-1][0] for h in hists]
    fnd = [min(r for r, a, *_ in h if a < 100) for h in hists]
    pdr = [np.mean([min(1.0, h[r][3]) for r in range(min(len(h), 1500))]) for h in hists]
    dly = [np.mean([h[r][4] for r in range(min(len(h), 1500))]) for h in hists]
    result[k] = {'LAST': ci(last), 'FND': ci(fnd), 'PDR': ci(pdr), 'DELAY': ci(dly)}

with open('eval_canonical.json', 'w') as f:
    json.dump(result, f, indent=2)

base = result['PEGASIS']['LAST'][0]
print(f'{"protocol":14s} {"LAST":>7s} {"CI":>6s} {"xPEG":>5s} {"FND":>6s} {"PDR":>5s} {"DELAY":>6s}')
for k in ['LEACH', 'PEGASIS', 'DEEC', 'SEP', 'DCK-LEACH22', 'NPSOP23',
          'CCH-K1', 'CCH-K2', 'CCH-K3', 'CCH-ADP', 'CCH-CLUSTK1', 'H-PEGASIS']:
    m, c = result[k]['LAST']
    print(f'{k:14s} {m:7.0f} ±{c:4.0f} {m/base:5.2f} {result[k]["FND"][0]:6.0f} '
          f'{result[k]["PDR"][0]:5.2f} {result[k]["DELAY"][0]:6.1f}')
