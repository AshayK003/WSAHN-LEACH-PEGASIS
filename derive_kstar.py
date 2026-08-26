"""Derive the analytically optimal chain length k* for ClusterChain.

ClusterChain is a 1-parameter family: k = number of relay nodes on the chain
(k = n_ch in sparse mode, k = N in dense mode). We minimise the per-round
energy E(k) from the Heinzelman first-order model and compare against the
empirical sweep.

Geometry (matches energy.py / run.py):
  N nodes, field 100x100, sink at (50,175) -> D = 125 m from field centre
  D0 = 87.7 m  ->  the sink hop is always multipath (D > D0)

Energy model per round (N alive nodes, all sense + report one packet):
  member->CH : (N-k) tx at free-space distance d_m ~ a/sqrt(k),  a = M/(2 sqrt(pi))
  CH Rx       : N receives
  aggregation : N packets fused
  chain relay : (k-1) tx at free-space distance d_c ~ b/k,        b = M/2
  chain Rx    : k receives
  terminus->sink : 1 multipath hop at distance D (E_mp * D^4)
"""
import numpy as np
from energy import E_ELEC, E_FS, E_MP, PACKET_SIZE

M = 100.0
D = 125.0
D0 = (E_FS / E_MP) ** 0.5
L = PACKET_SIZE
E_RX = L * E_ELEC
E_DA = L * 5e-9
a = M / (2 * np.sqrt(np.pi))
b = M / 2.0


def E_round(k: int, N: int) -> float:
    if k < 1:
        k = 1
    k = min(k, N)
    d_m2 = a * a / k
    e_member = (N - k) * (L * E_ELEC + L * E_FS * d_m2)
    e_ch_rx = N * E_RX
    e_da = N * E_DA
    d_c2 = b * b / (k * k)
    e_chain = (k - 1) * (L * E_ELEC + L * E_FS * d_c2)
    e_chain_rx = k * E_RX
    e_sink = L * E_ELEC + L * E_MP * (D ** 4)
    return e_member + e_ch_rx + e_da + e_chain + e_chain_rx + e_sink


def k_star(N: int) -> int:
    ks = range(1, N + 1)
    return min(ks, key=lambda k: E_round(k, N))


print(f"D0 = {D0:.1f} m ; sink D = {D:.1f} m (multipath)\n")
print("Per-round energy minimum E(k) and analytic k* for shrinking networks:")
print(f"{'N':>4} {'k*':>4} {'E(k*)':>11} {'E(k=5)':>11} {'E(k=7)':>11} {'E(k=N)':>11}")
table = []
for N in [100, 80, 60, 40, 20]:
    ks = k_star(N)
    e = E_round(ks, N)
    print(f"{N:>4} {ks:>4} {e:.4e} {E_round(5, N):.4e} {E_round(7, N):.4e} {E_round(N, N):.4e}")
    table.append((N, ks))

# fit a simple adaptive rule: k* ~ sqrt(N/2) clamped to [3, 12]
print("\nAdaptive rule candidates (k = clamp(round(sqrt(N/2)), 3, 12)):")
for N, _ in table:
    fitted = max(3, min(12, round((N / 2) ** 0.5)))
    print(f"  N={N:>3}  k*={k_star(N):>2}  fitted={fitted:>2}")

# save derivation artifacts
with open('kstar_result.txt', 'w') as f:
    f.write(f"D0={D0:.1f}\nD={D:.1f}\n")
    f.write("N,k_star,E_round\n")
    for N, ks in table:
        f.write(f"{N},{ks},{E_round(ks, N):.6e}\n")
print("\nSaved kstar_result.txt")
