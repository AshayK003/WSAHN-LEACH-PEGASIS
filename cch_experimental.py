"""Experimental ClusterChain-H variants to test review-proposed mechanisms.

Mechanisms under test (each isolated so any measured difference is attributable):

  1. Energy-gradient relay ordering  (replaces MST/NN geometry in chain build)
  2. Adaptive per-round chain count K
  3. Selective dual terminus (FAIL-OVER, not always-on second head):
       - a vice node is added ONLY to chains longer than VICE_MIN_LEN
         (long chains carry high aggregation burden on the terminus)
       - the vice does NOT relay extra data during normal rounds
       - it pays a sink hop ONLY when the primary terminus would die on that
         hop, recovering the round instead of clearing the whole chain

All variants subclass ClusterChainH and reuse its transmission logic /
energy model unchanged except where explicitly overridden, so results are a
clean A/B against the baseline multichain K=1.
"""
import math
import numpy as np
from clusterchain_h import (
    ClusterChainH, partition_into_chains, build_refined_chain, CCNodeH,
)
from energy import (
    tx_energy, rx_energy, da_energy, in_range,
    PACKET_SIZE, E_ELEC, E_MP,
)


def _eg_score(cur, cand, sink, avg_e, scale):
    w_e, w_d, w_p = 0.5, 0.3, 0.2
    e_term = cand.energy / (avg_e or 1.0)
    d = cur.distance_to(cand)
    cost_term = tx_energy(d) / (scale + 1e-18)
    cur_ds = cur.distance_to(sink)
    c_ds = cand.distance_to(sink)
    progress = (cur_ds - c_ds) / (cur_ds + 1e-9)
    return w_e * e_term - w_d * cost_term + w_p * progress


def build_eg_chain(pool, sink, rotate=True):
    """Energy-gradient relay ordering over `pool` (all alive nodes in a sector)."""
    pool = list(pool)
    if not pool:
        return []
    if len(pool) == 1:
        pool[0].chain_next = None
        pool[0].is_terminus = True
        return pool

    avg_e = float(np.mean([n.energy for n in pool])) or 1.0
    max_d = max(n.distance_to(sink) for n in pool) or 1.0
    scale = PACKET_SIZE * (E_ELEC + E_MP * max_d ** 4)

    term = max(pool, key=lambda n: (n.energy / avg_e, -n.distance_to(sink)))
    rest = [n for n in pool if n is not term]
    if not rest:
        term.chain_next = None
        term.is_terminus = True
        return [term]

    start = max(rest, key=lambda n: n.distance_to(sink))
    path = [start]
    used_id = {start.id}
    cur = start
    while cur is not term:
        cands = [c for c in pool if c.id not in used_id]
        if not cands:
            break
        nxt = max(cands, key=lambda c: _eg_score(cur, c, sink, avg_e, scale))
        path.append(nxt)
        used_id.add(nxt.id)
        cur = nxt
        if cur is term:
            break

    for n in pool:
        n.chain_next = None
        n.is_terminus = False
    for i, n in enumerate(path):
        if i + 1 < len(path):
            n.chain_next = path[i + 1].id
    term.is_terminus = True
    return path


def assign_vice(chain, sink, min_len=6):
    """Selective dual-terminus FAIL-OVER.

    Reset any stale vice flags, then (only for chains long enough to bear high
    terminus burden) pick the best vice = highest residual-energy margin,
    tie-break nearest sink, among non-terminus nodes. The vice is activated
    only on primary-terminus death during transmission (see _transmit override).
    """
    for n in chain:
        n.is_vice = False
        n.vice_of = None
    if len(chain) < min_len:
        return
    terminus = next((c for c in chain if c.is_terminus), None)
    if terminus is None:
        return
    avg_e = float(np.mean([n.energy for n in chain])) or 1.0
    cands = [c for c in chain if not c.is_terminus]
    if not cands:
        return
    vice = max(cands, key=lambda c: (c.energy / avg_e, -c.distance_to(sink)))
    vice.is_vice = True
    vice.vice_of = terminus.id


class ClusterChainExpt(ClusterChainH):
    """Experimental protocol. Flags:

    eg_relay=True        -> build chains via energy-gradient ordering
    adaptive_k_expt=True -> choose K per round from alive count
    dual_terminus=True   -> add selective fail-over vice node to long chains
    """

    def __init__(self, *a, eg_relay=False, adaptive_k_expt=False,
                 dual_terminus=False, vice_min_len=6, **kw):
        super().__init__(*a, **kw)
        self.eg_relay = eg_relay
        self.adaptive_k_expt = adaptive_k_expt
        self.dual_terminus = dual_terminus
        self.vice_min_len = vice_min_len
        self.class_history = []

    def _select_k(self, alive):
        if self.adaptive_k_expt:
            n = len(alive)
            return max(1, min(self.K, round(n / 20)))
        return self.K

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
                if c.chain_next is None:
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
                    # primary terminus died on the sink hop -> try vice failover
                    vo = getattr(terminus, 'vice_of', None)
                    vice = by_id.get(vo) if vo is not None else None
                    recovered = False
                    if vice is not None and vice.alive:
                        if not vice.consume(tx_energy(vice.distance_to(self.sink))):
                            recovered = True
                            total_tx += (tx_energy(d)
                                         + tx_energy(vice.distance_to(self.sink)))
                            delays.append(max(1, len(ordered)))
                    if not recovered:
                        for node in ordered:
                            delivered.discard(node.id)
                else:
                    total_tx += tx_energy(d)
                    delays.append(max(1, len(ordered)))
        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def step(self):
        self.round += 1
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            self.class_history.append((self.round, 0, 0))
            return {}
        self.alive_count = len(alive)

        k = max(1, min(self._select_k(alive), self.alive_count))
        raw_chains = partition_into_chains(alive, k)
        chains = []
        for ch in raw_chains:
            if self.eg_relay:
                built = build_eg_chain(ch, self.sink, rotate=self.rotate)
            else:
                built = build_refined_chain(ch, self.sink,
                                           rotate=self.rotate, refine=True)
            if self.dual_terminus:
                assign_vice(built, self.sink, self.vice_min_len)
            chains.append(built)
        m = self._transmit_multichain(chains)

        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = m['received'] / max(1, m['sent'])
        self.history.append((
            self.round, self.alive_count, m['tx'] + m['rx'], pdr,
            m['delay'], m['sent'], m['received'],
        ))
        n_adv = sum(1 for n in self.nodes if n.alive and n.is_advanced)
        n_norm = self.alive_count - n_adv
        self.class_history.append((self.round, n_adv, n_norm))
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr,
                'delay': m['delay'], 'energy': m['tx'] + m['rx']}
