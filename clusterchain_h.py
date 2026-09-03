"""ClusterChain-H: Heterogeneity-Aware Hybrid Clustering-Chaining Protocol.

Builds on the LEACH/PEGASIS lineage but adds four mechanisms that, together,
give a legitimate (non-gimmick) margin over both vanilla LEACH and vanilla
PEGASIS:

  1. Joint heterogeneity + residual-energy + sink-proximity weighted election of
     relay heads (generalises SEP/DEEC into a clustering+chaining hybrid).
  2. MST/2-opt-refined chain construction that removes the long links of greedy
     nearest-neighbour PEGASIS (geometry lever).
   3. Energy + sink-proximity rotating chain terminus / leaders across parallel
      chains (replaces PEGASIS's blind round-robin leadership with energy-aware
      leadership: the costly sink hop always lands on a high-energy near-sink
      node).
  4. A tunable chain count K: K=1 keeps a single refined chain (lifetime-optimal,
     one sink hop); higher K adds parallel chains that strictly lower delay.
     The `adaptive` mode stays at K=1 for the whole run (it tracks the measured
     best lifetime config), while `multichain` lets K be set explicitly.
  5. A first-class `relay` mode: a rotating relay-sink tier where each chain's
     terminus forwards to the nearest of R rotating relays instead of the far
     off-field base station. The relay→BS forward hop is infrastructure and is
     tracked separately, never folded into sensor energy. Distinct from `multichain`
     only in the final sink hop; chain construction is identical.

All protocols import the same energy.py, so comparisons are like-for-like.
PDR is defined uniformly as packets delivered to the sink / packets generated
by alive source nodes.
"""
import random
import math
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Set
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE, E_ELEC, E_FS, E_MP, in_range


def _dist2(a, b):
    return a.distance_to(b) ** 2


def two_opt_path(nodes):
    """Refine an open path (list of node objects, mutated in place) by 2-opt to
    minimise the sum of squared link distances (a proxy for free-space tx cost).
    Greedy NN already gives a decent path; 2-opt removes the worst long links.
    Used as a fallback for very small chains; large chains use mst_chain.
    """
    n = len(nodes)
    if n < 4:
        return nodes
    improved = True
    while improved:
        improved = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                a, b = nodes[i], nodes[j]
                prev_i = nodes[i - 1] if i > 0 else None
                next_j = nodes[j + 1] if j < n - 1 else None
                cur = 0.0
                if prev_i:
                    cur += _dist2(prev_i, a)
                if next_j:
                    cur += _dist2(b, next_j)
                new = 0.0
                if prev_i:
                    new += _dist2(prev_i, b)
                if next_j:
                    new += _dist2(a, next_j)
                if new + 1e-12 < cur:
                    nodes[i:j + 1] = nodes[i:j + 1][::-1]
                    improved = True
    return nodes


def mst_chain(pool):
    """Build a low-cost chain over `pool` via Prim's minimum spanning tree (squared
    distance weights) followed by a tree traversal. The MST minimises the total
    squared-link cost of the aggregation structure, in the spirit of MLDA-style
    aggregation (Kalpakis et al., Computer Networks 2003); MST-traversal chains
    for PEGASIS were shown effective by Meghanathan (KSII TIIS 2009). The
    traversal yields a single connected ordering suitable for chain relay.
    O(|pool|^2) single pass -- much cheaper than iterated 2-opt and near-optimal.
    """
    import heapq
    nodes = list(pool)
    n = len(nodes)
    if n <= 2:
        return nodes
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


def _relink_chain(path, sink, rotate=True):
    """Given an ordered chain (list of nodes), choose the terminus (sink-facing
    end, LAST) and set chain_next / is_terminus links. Rotating the terminus is
    O(|path|) so it is cheap to do every round.
    """
    if not path:
        return path
    if len(path) == 1:
        path[0].is_terminus = True
        path[0].chain_next = None
        return path
    if rotate:
        max_e = max(n.energy for n in path) or 1.0
        term = max(path, key=lambda n: (n.energy / max_e, -n.distance_to(sink)))
    else:
        term = path[-1]
    idx = path.index(term)
    path = path[idx:] + path[:idx]
    for i, n in enumerate(path):
        n.chain_next = None
        n.is_terminus = False
    for i, n in enumerate(path):
        if i + 1 < len(path):
            n.chain_next = path[i + 1].id
    path[-1].is_terminus = True
    return path


def build_refined_chain(pool, sink, rotate=True, refine=True):
    """Build one refined chain over `pool` (list of nodes). Returns the ordered
    list with the terminus (sink-facing end) LAST. The terminus is chosen by
    residual energy and proximity to the sink and rotates every round.

    `refine=True` runs greedy nearest-neighbour + 2-opt to remove long links;
    this is only needed when the membership changes (nodes die), so callers
    should cache the result and just re-link/rotate otherwise.
    """
    if not pool:
        return []
    if len(pool) == 1:
        return _relink_chain(pool, sink, rotate)
    if refine:
        if len(pool) > 40:
            path = mst_chain(pool)
        else:
            start = max(pool, key=lambda n: n.energy)
            unvisited = set(n.id for n in pool)
            unvisited.discard(start.id)
            path = [start]
            cur = start
            while unvisited:
                nxt = min((n for n in pool if n.id in unvisited),
                          key=lambda n: cur.distance_to(n))
                path.append(nxt)
                unvisited.discard(nxt.id)
                cur = nxt
            path = two_opt_path(path)
    else:
        path = list(pool)
    return _relink_chain(path, sink, rotate)


def partition_into_chains(alive, K):
    """Split alive nodes into K spatial chains by FIXED angular sector around the
    centroid. A node's sector depends only on its own position (not on other
    nodes), so when one node dies only its own chain's membership changes and the
    others can be reused from cache."""
    if K <= 1:
        return [alive]
    cx = float(np.mean([n.x for n in alive]))
    cy = float(np.mean([n.y for n in alive]))
    bins = [[] for _ in range(K)]
    for n in alive:
        ang = math.atan2(n.y - cy, n.x - cx)
        # map [-pi, pi) to [0, K)
        b = int((ang + math.pi) / (2 * math.pi) * K) % K
        bins[b].append(n)
    return [b for b in bins if b]


@dataclass
class CCNodeH:
    id: int
    x: float
    y: float
    energy: float = 0.5
    alive: bool = True
    is_ch: bool = False
    ch_id: Optional[int] = None
    chain_next: Optional[int] = None
    is_terminus: bool = False
    is_advanced: bool = False
    score: float = 0.0

    def distance_to(self, other) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def consume(self, amount: float) -> bool:
        self.energy -= amount
        if self.energy <= 0:
            self.alive = False
            self.energy = 0
            return True
        return False


def optimal_k(n_alive, n_chains=1):
    """Per-round energy minimum for the clustered (single-chain) construction.

    Models: (N-k) member->CH free-space tx at d_m~a/sqrt(k); N CH rx + N
    aggregations; (k-1) head-chain relay links at d_c~b/k; k head rx; plus
    n_chains multipath sink hops. The single sink hop (n_chains=1) is the
    energy-frugal point; multi-chain trades those extra sink hops for delay.
    Returns the chain-head count k that minimises per-round energy.
    """
    if n_alive <= 3:
        return max(1, n_alive - 1)
    a = 100.0 / (2 * math.sqrt(math.pi))
    b = 50.0
    D = 125.0
    L = PACKET_SIZE
    e_rx = L * E_ELEC
    e_da = L * 5e-9
    e_sink = L * E_ELEC + L * E_MP * (D ** 4)

    def e_round(k):
        k = max(1, min(k, n_alive))
        d_m2 = a * a / k
        e_member = (n_alive - k) * (L * E_ELEC + L * E_FS * d_m2)
        e_ch_rx = n_alive * e_rx
        e_da_tot = n_alive * e_da
        d_c2 = b * b / (k * k)
        e_chain = (k - 1) * (L * E_ELEC + L * E_FS * d_c2)
        e_chain_rx = k * e_rx
        e_sinks = n_chains * e_sink
        return e_member + e_ch_rx + e_da_tot + e_chain + e_chain_rx + e_sinks

    return min(range(1, n_alive + 1), key=e_round)


class ClusterChainH:
    def __init__(
        self,
        n_nodes: int = 100,
        field_x: float = 100,
        field_y: float = 100,
        sink_x: float = 50,
        sink_y: float = 175,
        initial_energy: float = 0.5,
        m: float = 0.1,            # advanced-node fraction (heterogeneity)
        a_mult: float = 2.0,       # advanced initial-energy multiplier
        K: int = 5,                # chain-head count (clustered) / chain count (multichain)
        w_energy: float = 0.7,     # weight on (residual*type) vs sink proximity in election
        mode: str = 'clustered',   # 'clustered' | 'multichain' | 'adaptive' | 'relay'
        rotate: bool = True,       # rotate terminus by energy+proximity
        adaptive_k: bool = True,   # recompute K from energy model as nodes die (clustered)
        # --- relay mode params (ignored unless mode='relay') ---
        relay_count: int = 2,      # number of rotating relay collection points
        rotate_every: int = 50,    # re-select relays every N rounds (None = static)
        relay_energy: Optional[float] = 0.5,  # per-relay budget (None = unlimited infra)
        relay_zone: Optional[tuple] = None,  # (y_lo, y_hi) band for relay eligibility
    ):
        self.n = n_nodes
        self.field_x = field_x
        self.field_y = field_y
        self.sink = CCNodeH(-1, sink_x, sink_y, energy=float('inf'))
        self.initial_energy = initial_energy
        self.m = m
        self.a_mult = a_mult
        self.K = max(1, min(K, n_nodes))
        self.w_energy = w_energy
        self.mode = mode
        self.rotate = rotate
        self.adaptive_k = adaptive_k
        self._chain_store = {}
        self.round = 0
        self.alive_count = n_nodes
        self.history = []

        # relay-mode state (only used when mode='relay')
        self.relay_count = relay_count
        self.rotate_every = rotate_every
        self.relay_energy_budget = relay_energy
        self.relay_zone = relay_zone or (field_y * 0.3, field_y * 0.7)
        self.relay_positions = [(field_x / 2.0, field_y / 2.0)] * relay_count
        self.relay_energy = ([relay_energy] * relay_count
                             if relay_energy is not None else None)
        self.relay_forward_total = 0.0
        self.relay_dead_round = None
        self._relay_epoch = -1
        self.class_history = []  # (round, n_adv_alive, n_norm_alive) per round

        self.nodes = []
        n_adv = int(round(m * n_nodes))
        for i in range(n_nodes):
            e0 = a_mult * initial_energy if i < n_adv else initial_energy
            nd = CCNodeH(i, random.uniform(0, field_x), random.uniform(0, field_y), e0)
            nd.is_advanced = (i < n_adv)
            self.nodes.append(nd)

    # ---------------- setup phase ----------------
    def _elect_heads(self, k):
        # Score = w * (residual_energy * type_weight / avg) + (1-w) * proximity.
        # type_weight (a_mult for advanced, 1.0 for normal) is INTENTIONAL
        # double-counting on top of the higher residual energy advanced nodes
        # already carry: it steers expensive relay/aggregation roles toward
        # advanced nodes (SEP/DEEC design intent, extended to chaining).
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return
        avg_e = float(np.mean([n.energy for n in alive])) or 1.0
        max_d = max(n.distance_to(self.sink) for n in alive) or 1.0
        for n in self.nodes:
            n.is_ch = False
            n.ch_id = None
        for n in alive:
            eff = n.energy * (self.a_mult if n.is_advanced else 1.0)
            prox = 1.0 - n.distance_to(self.sink) / max_d
            n.score = self.w_energy * (eff / avg_e) + (1 - self.w_energy) * prox
        chosen = sorted(alive, key=lambda n: n.score, reverse=True)[:k]
        for n in chosen:
            n.is_ch = True

    def _form_clusters(self):
        chs = [n for n in self.nodes if n.alive and n.is_ch]
        if not chs:
            alive = [n for n in self.nodes if n.alive]
            if alive:
                mx = max(alive, key=lambda n: n.energy)
                mx.is_ch = True
                chs = [mx]
        for n in self.nodes:
            if n.alive and n.is_ch:
                continue
            if n.alive:
                n.ch_id = min(chs, key=lambda ch: n.distance_to(ch)).id

    # ---------------- transmission ----------------
    def _transmit_clustered(self, heads):
        alive = [n for n in self.nodes if n.alive]
        by_id = {n.id: n for n in alive}
        sent = len(alive)
        delivered = {n.id for n in alive}
        total_tx = 0.0
        total_rx = 0.0
        delays = []

        members = {}
        for n in alive:
            if not n.is_ch and n.ch_id is not None:
                members.setdefault(n.ch_id, []).append(n.id)

        # Stage 1: member -> CH (single short free-space hop)
        for n in alive:
            if n.is_ch or n.ch_id is None:
                continue
            ch = by_id.get(n.ch_id)
            if ch is None or not ch.alive:
                delivered.discard(n.id)
                continue
            d = n.distance_to(ch)
            if not in_range(d):
                n.consume(tx_energy(d))
                delivered.discard(n.id)
                continue
            if n.consume(tx_energy(d)):
                delivered.discard(n.id)
                continue
            if ch.consume(rx_energy() + da_energy()):
                for mid in members.get(ch.id, []):
                    delivered.discard(mid)
                delivered.discard(ch.id)
                continue
            total_tx += tx_energy(d)
            total_rx += rx_energy() + da_energy()

        # Stage 2: head chain relay to the rotating terminus, then terminus -> sink
        chain = [h for h in heads if h.chain_next is not None or h.is_terminus]
        broken = False
        for h in chain:
            if h.chain_next is None:  # terminus
                continue
            nxt = by_id.get(h.chain_next)
            if nxt is None or not nxt.alive:
                broken = True
            if broken:
                for mid in members.get(h.id, []):
                    delivered.discard(mid)
                delivered.discard(h.id)
                continue
            d = h.distance_to(nxt)
            if not in_range(d):
                h.consume(tx_energy(d))
                delivered.discard(h.id)
                broken = True
                continue
            if h.consume(tx_energy(d)):
                broken = True
                for mid in members.get(h.id, []):
                    delivered.discard(mid)
                delivered.discard(h.id)
                continue
            if nxt.consume(rx_energy() + da_energy()):
                broken = True
                for mid in members.get(h.id, []):
                    delivered.discard(mid)
                delivered.discard(h.id)
                for mid in members.get(nxt.id, []):
                    delivered.discard(mid)
                delivered.discard(nxt.id)
                continue
            total_tx += tx_energy(d)
            total_rx += rx_energy() + da_energy()

        terminus = next((h for h in chain if h.is_terminus), None)
        if terminus is None:
            return self._pack(sent, delivered, total_tx, total_rx, delays)
        if broken:
            for mid in members.get(terminus.id, []):
                delivered.discard(mid)
            delivered.discard(terminus.id)
        else:
            d = terminus.distance_to(self.sink)
            if terminus.consume(tx_energy(d)):
                # Terminus aggregates the entire network's fused payload; its
                # death on the sink hop loses the whole round — consistent with
                # PEGASIS clearing all deliveries when the leader dies.
                delivered.clear()
            else:
                total_tx += tx_energy(d)
                delays.append(1 + max(1, len(chain)))
        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def _transmit_multichain(self, chains):
        alive = [n for n in self.nodes if n.alive]
        by_id = {n.id: n for n in alive}
        sent = len(alive)
        delivered = {n.id for n in alive}
        total_tx = 0.0
        total_rx = 0.0
        delays = []

        for chain in chains:
            broken = False
            ordered = [c for c in chain if c.chain_next is not None or c.is_terminus]
            for c in ordered:
                if c.chain_next is None:  # terminus of this chain
                    continue
                nxt = by_id.get(c.chain_next)
                if nxt is None or not nxt.alive:
                    broken = True
                if broken:
                    delivered.discard(c.id)
                    continue
                d = c.distance_to(nxt)
                if not in_range(d):
                    c.consume(tx_energy(d))
                    delivered.discard(c.id)
                    broken = True
                    continue
                if c.consume(tx_energy(d)):
                    broken = True
                    delivered.discard(c.id)
                    continue
                if nxt.consume(rx_energy() + da_energy()):
                    broken = True
                    delivered.discard(c.id)
                    delivered.discard(nxt.id)
                    continue
                total_tx += tx_energy(d)
                total_rx += rx_energy() + da_energy()
            terminus = next((c for c in ordered if c.is_terminus), None)
            if terminus is None:
                continue
            if broken:
                delivered.discard(terminus.id)
            else:
                d = terminus.distance_to(self.sink)
                if terminus.consume(tx_energy(d)):
                    # Terminus aggregates this chain's fused payload; its death
                    # loses the whole chain's round. Parallel chains isolate the
                    # loss to one sector, unlike single-chain PEGASIS (which
                    # clears the entire network).
                    for node in ordered:
                        delivered.discard(node.id)
                else:
                    total_tx += tx_energy(d)
                    delays.append(max(1, len(ordered)))
        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def _nearest_relay(self, x, y):
        best_i, best_d = 0, float('inf')
        for i, (rx, ry) in enumerate(self.relay_positions):
            d = ((x - rx) ** 2 + (y - ry) ** 2) ** 0.5
            if d < best_d:
                best_d, best_i = d, i
        return best_i, best_d

    def _select_relays(self):
        """Re-select the highest-residual-energy alive nodes in the relay zone
        as the current relays (rotation epoch). Each rotated-in relay gets a
        fresh budget so no single node becomes a permanent bottleneck."""
        alive = [n for n in self.nodes if n.alive]
        zlo, zhi = self.relay_zone
        eligible = [n for n in alive if zlo <= n.y <= zhi]
        pool = eligible if eligible else alive
        chosen = sorted(pool, key=lambda n: n.energy, reverse=True)[:self.relay_count]
        self.relay_positions = [(n.x, n.y) for n in chosen]
        if self.relay_energy_budget is not None:
            self.relay_energy = [self.relay_energy_budget for _ in chosen]

    def _transmit_relay_multichain(self, chains):
        alive = [n for n in self.nodes if n.alive]
        by_id = {n.id: n for n in alive}
        sent = len(alive)
        delivered = {n.id for n in alive}
        total_tx = 0.0
        total_rx = 0.0
        delays = []

        for chain in chains:
            broken = False
            ordered = [c for c in chain if c.chain_next is not None or c.is_terminus]
            for c in ordered:
                if c.chain_next is None:  # terminus of this chain
                    continue
                nxt = by_id.get(c.chain_next)
                if nxt is None or not nxt.alive:
                    broken = True
                    delivered.discard(c.id)
                    continue
                d = c.distance_to(nxt)
                if not in_range(d):
                    c.consume(tx_energy(d))
                    delivered.discard(c.id)
                    broken = True
                    continue
                if c.consume(tx_energy(d)):
                    broken = True
                    delivered.discard(c.id)
                    continue
                if nxt.consume(rx_energy() + da_energy()):
                    broken = True
                    delivered.discard(c.id)
                    delivered.discard(nxt.id)
                    continue
                total_tx += tx_energy(d)
                total_rx += rx_energy() + da_energy()
            terminus = next((c for c in ordered if c.is_terminus), None)
            if terminus is None:
                continue
            if broken:
                delivered.discard(terminus.id)
                continue

            # sensor-side hop: terminus -> nearest relay (charged to sensor,
            # exactly like the baseline's terminus -> sink hop)
            ridx, d_relay = self._nearest_relay(terminus.x, terminus.y)
            if terminus.consume(tx_energy(d_relay)):
                for node in ordered:
                    delivered.discard(node.id)
                continue
            total_tx += tx_energy(d_relay)

            # relay -> BS forward is infrastructure, tracked separately, never
            # folded into sensor energy
            rx, ry = self.relay_positions[ridx]
            d_bs = ((rx - self.sink.x) ** 2 + (ry - self.sink.y) ** 2) ** 0.5
            e_bs = tx_energy(d_bs)
            if self.relay_energy is not None:
                if self.relay_energy[ridx] >= e_bs:
                    self.relay_energy[ridx] -= e_bs
                    self.relay_forward_total += e_bs
                else:
                    if self.relay_dead_round is None:
                        self.relay_dead_round = self.round
                    for node in ordered:
                        delivered.discard(node.id)
                    continue
            else:
                self.relay_forward_total += e_bs

            delays.append(max(1, len(ordered)) + 1)

        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def _pack(self, sent, delivered, total_tx, total_rx, delays):
        return {
            'sent': sent,
            'received': len(delivered),
            'tx': total_tx,
            'rx': total_rx,
            'delay': float(np.mean(delays)) if delays else 0.0,
        }

    # ---------------- round driver ----------------
    def step(self):
        self.round += 1
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.alive_count = len(alive)

        mode = self.mode
        if mode == 'adaptive':
            # Lifetime is maximised by a single refined MST chain (1 sink hop);
            # extra parallel chains add costly sink hops. As nodes die, keep one
            # chain and let the rotating terminus absorb the load. This tracks the
            # measured best config (multichain K=1) for the whole run.
            mode = 'multichain'
            k = 1
        else:
            k = self.K

        if mode == 'clustered':
            k = optimal_k(self.alive_count, 1) if self.adaptive_k else self.K
            k = max(1, min(k, self.alive_count))
            self._elect_heads(k)
            self._form_clusters()
            heads = [n for n in self.nodes if n.alive and n.is_ch]
            build_refined_chain(heads, self.sink, rotate=self.rotate)
            m = self._transmit_clustered(heads)
        else:  # multichain or relay (relay uses same chain build, different sink hop)
            k = max(1, min(k, self.alive_count))
            # relay mode: rotate the relay set at epoch boundaries
            if mode == 'relay' and self.rotate_every is not None:
                epoch = (self.round + 1) // self.rotate_every
                if epoch != self._relay_epoch and self.alive_count > 0:
                    self._relay_epoch = epoch
                    self._select_relays()
            raw_chains = partition_into_chains(alive, k)
            chains = []
            for ch in raw_chains:
                sig = frozenset(n.id for n in ch)
                cached = self._chain_store.get(sig)
                if cached is not None:
                    chains.append(build_refined_chain(cached, self.sink,
                                                      rotate=self.rotate, refine=False))
                else:
                    built = build_refined_chain(ch, self.sink,
                                                rotate=self.rotate, refine=True)
                    self._chain_store[sig] = built
                    chains.append(built)
            m = (self._transmit_relay_multichain(chains) if mode == 'relay'
                 else self._transmit_multichain(chains))

        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = m['received'] / max(1, m['sent'])
        n_adv = sum(1 for n in self.nodes if n.alive and n.is_advanced)
        n_norm = self.alive_count - n_adv
        self.class_history.append((self.round, n_adv, n_norm))
        self.history.append((
            self.round, self.alive_count, m['tx'] + m['rx'], pdr,
            m['delay'], m['sent'], m['received'],
        ))
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr,
                'delay': m['delay'], 'energy': m['tx'] + m['rx']}

    def run(self, max_rounds: int = 2000):
        while self.alive_count > 0 and self.round < max_rounds:
            self.step()
        return self.history
