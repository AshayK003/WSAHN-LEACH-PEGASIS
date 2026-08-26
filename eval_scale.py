"""Scalability check (core protocols) with streamed logging."""
import json, time, numpy as np
from leach import LEACH
from pegasis import PEGASIS
from sep import SEP
from deec import DEEC
from clusterchain_h import ClusterChainH

M, A, MAXR = 0.1, 2.0, 4000

def run(cls, n, seeds, **kw):
    out = []
    for s in seeds:
        np.random.seed(s)
        out.append(cls(n_nodes=n, **kw).run(MAXR))
    return out

def milestone(hists, n, frac):
    return np.array([next((r for r, a, *_ in h if a <= frac*n), h[-1][0]) for h in hists if h])

def metrics(hists, n):
    fnd=milestone(hists,n,1.0); hnd=milestone(hists,n,0.5)
    last=np.array([h[-1][0] for h in hists if h])
    pdr=[]; dly=[]; ed=[]
    for h in hists:
        w=min(len(h),1500)
        pdr.append(float(np.mean([min(1.0,h[r][3]) for r in range(w)])))
        d=float(np.mean([h[r][4] for r in range(w)])); dly.append(d)
        ed.append(float(np.mean([h[r][2] for r in range(w)])*d))
    return {'LAST':(last.mean(),1.96*last.std(ddof=1)/np.sqrt(len(last))),
            'HND':(hnd.mean(),0),'PDR':(np.mean(pdr),0),'DELAY':(np.mean(dly),0),
            'E_x_D':(np.mean(ed),0)}

def core(n, seeds):
    return {
        'LEACH': run(LEACH,n,seeds),
        'PEGASIS': run(PEGASIS,n,seeds),
        'SEP': run(SEP,n,seeds,m=M,a_mult=A),
        'DEEC': run(DEEC,n,seeds,m=M,a_mult=A),
        'PEGASIS-MST': run(ClusterChainH,n,seeds,m=0.0,a_mult=1.0,mode='multichain',K=1),
        'CCH-K2': run(ClusterChainH,n,seeds,m=M,a_mult=A,mode='multichain',K=2),
        'CCH-K3': run(ClusterChainH,n,seeds,m=M,a_mult=A,mode='multichain',K=3),
    }

res={}
for n,seeds in [(200,[2000+i*11 for i in range(8)]), (500,[3000+i*13 for i in range(5)])]:
    t=time.time(); print(f"== N={n} ==", flush=True)
    res[str(n)]={k:metrics(v,n) for k,v in core(n,seeds).items()}
    for k,m in res[str(n)].items():
        print(f"  {k:14s} LAST={m['LAST'][0]:.0f} PDR={m['PDR'][0]:.2f} DELAY={m['DELAY'][0]:.1f} ExD={m['E_x_D'][0]:.4f}", flush=True)
    print(f"  ({time.time()-t:.1f}s)", flush=True)

json.dump(res, open('eval_scale.json','w'), indent=2)
print("saved eval_scale.json", flush=True)
