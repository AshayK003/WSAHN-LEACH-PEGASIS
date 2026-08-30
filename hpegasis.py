"""H-PEGASIS baseline — geometry-refined PEGASIS with a rotating leader.

Implements the structural half of ClusterChain-H's contribution as a *standalone*
baseline, so the paper can quantify the geometry+rotation gain independently of the
heterogeneity-election gain:

  * Chain is built with Prim's MST (squared-distance weights) instead of greedy
    nearest-neighbour, then traversed into a single ordering — removes PEGASIS's
    long greedy links (the H-PEGASIS structural mechanism).
  * The sink-facing terminus is the alive node maximising residual energy and
    proximity to the sink, rotated every round (the rotating-leader mechanism),
    instead of a fixed chain-end leader.
  * Homogeneous by default: no SEP/DEEC heterogeneity-aware election. This is
    deliberate — H-PEGASIS isolates the *geometry* contribution; ClusterChain-H
    adds the heterogeneity-election contribution on top.

Transmission logic is inherited unchanged from PEGASIS (same energy.py, same
PDR/delay semantics), so the comparison is strictly like-for-like.
"""
import heapq
import math

from pegasis import PEGASIS, PegNode
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE, E_FS, E_MP


def _mst_chain(nodes):
    """Prim's MST over `nodes` (squared-distance weights), returned as a traversal
    ordering. Mirrors clusterchain_h.mst_chain but operates on PegNode objects."""
    nodes = list(nodes)
    n = len(nodes)
    if n <= 2:
        return list(nodes)
    idx = {nd.id: nd for nd in nodes}
    start = max(nodes, key=lambda x: x.energy)
    dist = {nd.id: float('inf') for nd in nodes}
    dist[start.id] = 0.0
    visited = set()
    pq = [(0.0, start.id)]
    order = []
    while pq:
        d, uid = heapq.heappop(pq)
        if uid in visited:
            continue
        visited.add(uid)
        u = idx[uid]
        if u is not start:
            order.append(u)
        for v in nodes:
            if v.id in visited:
                continue
            w = u.distance_to(v) ** 2
            if w < dist[v.id]:
                dist[v.id] = w
                heapq.heappush(pq, (w, v.id))
    return [start] + order


class HPEGASIS(PEGASIS):
    def _build_chain(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return
        for n in self.nodes:
            n.next_id = None
            n.is_leader = False

        # MST-refined chain (geometry mechanism)
        chain = _mst_chain(alive)

        # Rotating terminus (leader) by residual energy + sink proximity
        max_e = max(n.energy for n in chain) or 1.0
        term = max(chain, key=lambda n: (n.energy / max_e,
                                         -n.distance_to(self.sink)))
        rot = chain.index(term)
        chain = chain[rot:] + chain[:rot]

        for i, n in enumerate(chain):
            if i + 1 < len(chain):
                n.next_id = chain[i + 1].id
        chain[-1].is_leader = True
        chain[-1].rounds_as_leader += 1
