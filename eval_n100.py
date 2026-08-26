"""Focused N=100 evaluation (current MST code) -> eval_n100.json + lifetime.png."""
import json, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH

M, A, MAXR = 0.1, 2.0, 4000
SEEDS = [1000 + i * 7 for i in range(20)]

def run(cls, **kw):
    return [cls(n_nodes=100, **kw).run(MAXR) for s in SEEDS for _ in [np.random.seed(s)][:1]]

def run(cls, **kw):
    out=[]
    for s in SEEDS:
        np.random.seed(s); out.append(cls(n_nodes=100,**kw).run(MAXR))
    return out

def ms(hists):
    last=np.array([h[-1][0] for h in hists if h])
    hnd=np.array([next((r for r,a,*_ in h if a<=50),h[-1][0]) for h in hists if h])
    pdr=np.mean([float(np.mean([min(1.0,h[r][3]) for r in range(min(len(h),1500))])) for h in hists])
    dly=np.mean([float(np.mean([h[r][4] for r in range(min(len(h),1500))])) for h in hists])
    ed=np.mean([float(np.mean([h[r][2] for r in range(min(len(h),1500))]))*dly for h in hists])
    return {'LAST':(last.mean(),1.96*last.std(ddof=1)/np.sqrt(len(last))),
            'HND':(hnd.mean(),1.96*hnd.std(ddof=1)/np.sqrt(len(hnd))),
            'PDR':pdr,'DELAY':dly,'E_x_D':ed}

protos = {
    'LEACH': run(LEACH),
    'PEGASIS': run(PEGASIS),
    'SEP': run(SEP, m=M, a_mult=A),
    'DEEC': run(DEEC, m=M, a_mult=A),
    'PEGASIS-MST': run(ClusterChainH, m=0.0, a_mult=1.0, mode='multichain', K=1),
    'CCH-K1': run(ClusterChainH, m=M, a_mult=A, mode='multichain', K=1),
    'CCH-K2': run(ClusterChainH, m=M, a_mult=A, mode='multichain', K=2),
    'CCH-K3': run(ClusterChainH, m=M, a_mult=A, mode='multichain', K=3),
}
res = {k: ms(v) for k, v in protos.items()}
pg = res['PEGASIS']['LAST'][0]; le = res['LEACH']['LAST'][0]
print(f"{'Protocol':14s} {'FND':>5s} {'HND':>6s} {'LAST':>6s} {'xPEG':>5s} {'xPDR':>5s} {'DELAY':>6s} {'E×D':>8s}")
for k, m in res.items():
    print(f"{k:14s} {m['HND'][0]:5.0f} {m['HND'][0]:6.0f} {m['LAST'][0]:6.0f} "
          f"{m['LAST'][0]/pg:5.2f} {m['PDR']:5.2f} {m['DELAY']:6.1f} {m['E_x_D']:8.4f}")
json.dump({k: {kk: (vv if isinstance(vv, float) else list(vv)) for kk, vv in v.items()}
            for k, v in res.items()}, open('eval_n100.json', 'w'), indent=2)

order = list(res.keys())
means = [res[k]['LAST'][0] for k in order]
errs = [res[k]['LAST'][1] for k in order]
plt.figure(figsize=(10, 5))
plt.bar(order, means, yerr=errs, capsize=4, color='#2ca02c')
plt.ylabel('Network lifetime (rounds)'); plt.title('N=100 heterogeneous: lifetime ±95% CI')
plt.xticks(rotation=20)
for i, v in enumerate(means): plt.text(i, v, f'{v:.0f}', ha='center', va='bottom', fontsize=8)
plt.tight_layout(); plt.savefig('lifetime.png', dpi=150); plt.close()
print("saved eval_n100.json, lifetime.png")
