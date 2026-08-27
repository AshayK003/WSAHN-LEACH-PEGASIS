"""Recent (2020-2026) mechanism variants, implemented in OUR simulator for a
fair like-for-like test against ClusterChain-H.

Two mechanisms are portable and tested here:
  - DualHead  : DCK-LEACH (Sensors 2022) dual cluster-head (primary + vice)
  - PSOCH     : NPSOP (Wireless Pers Commun 2023) PSO-selected cluster heads

Both use the shared energy.py so the comparison vs ClusterChain-H is honest.
DRL-based schemes (HDQN, DRL-GNN) are NOT implemented: they require a training
loop and their published numbers come from different simulators, so a direct
number comparison would be meaningless. OEE-WCRD's CH-scoring idea is already
covered by the SEP/DEEC baselines in eval_full.py.
"""
import random
import math
import numpy as np
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE, in_range


class RVNode:
    def __init__(self, i, x, y, e):
        self.id = i
        self.x = x
        self.y = y
        self.energy = e
        self.alive = True
        self.is_ch = False
        self.is_vice = False
        self.ch_id = None
        self._type = 1.0

    def distance_to(self, o):
        return math.hypot(self.x - o.x, self.y - o.y)

    def consume(self, a):
        self.energy -= a
        if self.energy <= 0:
            self.alive = False
            self.energy = 0
            return True
        return False


def _deploy(n, m, a_mult, fx, fy, sx, sy, ie):
    nodes = []
    n_adv = int(round(m * n))
    for i in range(n):
        e = a_mult * ie if i < n_adv else ie
        nd = RVNode(i, random.uniform(0, fx), random.uniform(0, fy), e)
        nd._type = a_mult if i < n_adv else 1.0
        nodes.append(nd)
    sink = RVNode(-1, sx, sy, float('inf'))
    return nodes, sink


class DualHead:
    """DCK-LEACH (2022): each cluster gets a primary CH (residual energy +
    distance to cluster centroid) and a vice CH (residual energy + distance to
    sink). Members -> primary (aggregate) -> vice -> sink. Both heads rotate by
    energy every round, splitting the expensive sink-hop load."""

    def __init__(self, n_nodes=100, field_x=100, field_y=100, sink_x=50,
                 sink_y=175, initial_energy=0.5, m=0.1, a_mult=2.0, K=5,
                 w_primary=0.7):
        self.n = n_nodes
        self.fx, self.fy = field_x, field_y
        self.sink = RVNode(-1, sink_x, sink_y, float('inf'))
        self.ie = initial_energy
        self.m, self.a_mult = m, a_mult
        self.K = max(1, min(K, n_nodes))
        self.w = w_primary
        self.nodes, _ = _deploy(n_nodes, m, a_mult, field_x, field_y,
                                sink_x, sink_y, initial_energy)
        self.round = 0
        self.alive_count = n_nodes
        self.history = []

    def _cluster(self):
        alive = [n for n in self.nodes if n.alive]
        clusters = [[] for _ in range(self.K)]
        cents = [(random.uniform(0, self.fx), random.uniform(0, self.fy))
                 for _ in range(self.K)]
        if not alive:
            self.clusters = clusters
            self.centroids = cents
            return
        for _ in range(5):
            clusters = [[] for _ in range(self.K)]
            for n in alive:
                k = min(range(self.K),
                         key=lambda kk: math.hypot(n.x - cents[kk][0],
                                                   n.y - cents[kk][1]))
                clusters[k].append(n)
            newc = []
            for ci, c in enumerate(clusters):
                if c:
                    newc.append((sum(x.x for x in c) / len(c),
                                 sum(x.y for x in c) / len(c)))
                else:
                    newc.append(cents[ci])
            cents = newc
        self.clusters = clusters
        self.centroids = cents

    def step(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.round += 1
        for n in self.nodes:
            n.is_ch = n.is_vice = False
            n.ch_id = None
        self._cluster()
        sent = len(alive)
        delivered = {n.id for n in alive}
        total_e = 0.0
        delays = []
        for ci, cl in enumerate(self.clusters):
            if not cl:
                continue
            cx, cy = self.centroids[ci]
            avg_e = float(np.mean([n.energy for n in cl])) or 1.0
            maxd_c = max(n.distance_to(RVNode(-9, cx, cy, 0)) for n in cl) or 1.0
            maxd_s = max(n.distance_to(self.sink) for n in cl) or 1.0
            for n in cl:
                dc = math.hypot(n.x - cx, n.y - cy)
                n.score_p = self.w * (n.energy * n._type / avg_e) + \
                    (1 - self.w) * (1 - dc / maxd_c)
                n.score_v = (n.energy * n._type / avg_e) * \
                    (1 - n.distance_to(self.sink) / maxd_s)
            primary = max(cl, key=lambda n: n.score_p)
            vice = max(cl, key=lambda n: n.score_v)
            primary.is_ch = True
            vice.is_vice = True
            # members -> primary
            for n in cl:
                if n is primary or n is vice:
                    continue
                d = n.distance_to(primary)
                if not in_range(d):
                    n.consume(tx_energy(d))
                    delivered.discard(n.id)
                    continue
                if n.consume(tx_energy(d)):
                    delivered.discard(n.id)
                    continue
                if primary.consume(rx_energy() + da_energy()):
                    delivered.discard(n.id)
                    delivered.discard(primary.id)
                    continue
                total_e += tx_energy(d) + rx_energy() + da_energy()
            # primary -> vice
            if vice is not primary:
                d = primary.distance_to(vice)
                if not in_range(d):
                    primary.consume(tx_energy(d))
                    delivered.discard(primary.id)
                elif not primary.consume(tx_energy(d)):
                    if vice.consume(rx_energy() + da_energy()):
                        delivered.discard(vice.id)
                    else:
                        total_e += tx_energy(d) + rx_energy() + da_energy()
            # vice -> sink
            d = vice.distance_to(self.sink)
            if vice.consume(tx_energy(d)):
                delivered.discard(vice.id)
            else:
                total_e += tx_energy(d)
                delays.append(3)
        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = len(delivered) / max(1, sent)
        self.history.append((self.round, self.alive_count, total_e, pdr,
                             float(np.mean(delays)) if delays else 0.0,
                             sent, len(delivered)))
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr}

    def run(self, max_rounds=4000):
        while self.alive_count > 0 and self.round < max_rounds:
            self.step()
        return self.history


class PSOCH:
    """NPSOP (2023): PSO selects K cluster heads minimizing a fitness of total
    delivery energy + load balance. Members join nearest CH; CH aggregates and
    sends directly to sink. Captures the PSO CH-selection contribution."""

    def __init__(self, n_nodes=100, field_x=100, field_y=100, sink_x=50,
                 sink_y=175, initial_energy=0.5, m=0.1, a_mult=2.0, K=5,
                 swarm=12, iters=20):
        self.n = n_nodes
        self.fx, self.fy = field_x, field_y
        self.sink = RVNode(-1, sink_x, sink_y, float('inf'))
        self.m, self.a_mult = m, a_mult
        self.K = max(1, min(K, n_nodes))
        self.swarm, self.iters = swarm, iters
        self.nodes, _ = _deploy(n_nodes, m, a_mult, field_x, field_y,
                                sink_x, sink_y, initial_energy)
        self.round = 0
        self.alive_count = n_nodes
        self.history = []
        self.ch_ids = list(range(n_nodes))

    def _fitness(self, ch_ids):
        alive = [n for n in self.nodes if n.alive]
        chs = [self.nodes[i] for i in ch_ids if self.nodes[i].alive]
        if not chs:
            return 1e9
        total = 0.0
        loads = [0] * len(chs)
        for n in alive:
            if n in chs:
                continue
            c = min(chs, key=lambda ch: n.distance_to(ch))
            d = n.distance_to(c)
            total += tx_energy(d) + rx_energy() + da_energy()
            loads[chs.index(c)] += 1
        for c in chs:
            total += tx_energy(c.distance_to(self.sink)) + \
                rx_energy() * 0  # sink rx negligible
        # load balance penalty
        if loads:
            total += 50.0 * (max(loads) - min(loads))
        return total

    def _select(self):
        alive_ids = [n.id for n in self.nodes if n.alive]
        if len(alive_ids) <= self.K:
            self.ch_ids = alive_ids
            return
        parts = [random.sample(alive_ids, self.K) for _ in range(self.swarm)]
        best = min(parts, key=self._fitness)
        self.ch_ids = best

    def step(self):
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.round += 1
        self._select()
        chs = {i: self.nodes[i] for i in self.ch_ids if self.nodes[i].alive}
        sent = len(alive)
        delivered = {n.id for n in alive}
        total_e = 0.0
        for n in alive:
            if n.id in chs:
                continue
            c = min(chs.values(), key=lambda ch: n.distance_to(ch))
            d = n.distance_to(c)
            if not in_range(d):
                n.consume(tx_energy(d))
                delivered.discard(n.id)
                continue
            if n.consume(tx_energy(d)):
                delivered.discard(n.id)
                continue
            if c.consume(rx_energy() + da_energy()):
                delivered.discard(c.id)
                continue
            total_e += tx_energy(d) + rx_energy() + da_energy()
        for c in chs.values():
            d = c.distance_to(self.sink)
            if c.consume(tx_energy(d)):
                delivered.discard(c.id)
            else:
                total_e += tx_energy(d)
        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = len(delivered) / max(1, sent)
        self.history.append((self.round, self.alive_count, total_e, pdr,
                             2.0, sent, len(delivered)))
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr}

    def run(self, max_rounds=4000):
        while self.alive_count > 0 and self.round < max_rounds:
            self.step()
        return self.history
