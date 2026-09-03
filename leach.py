"""LEACH Protocol Implementation"""
import random
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE, in_range


@dataclass
class Node:
    id: int
    x: float
    y: float
    energy: float = 0.5  # J
    alive: bool = True
    is_ch: bool = False
    ch_id: Optional[int] = None
    rounds_as_ch: int = 0
    last_ch_round: int = -1000

    def distance_to(self, other: 'Node') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def consume(self, amount: float) -> bool:
        self.energy -= amount
        if self.energy <= 0:
            self.alive = False
            self.energy = 0
            return True
        return False


class LEACH:
    def __init__(
        self,
        n_nodes: int = 100,
        field_x: float = 100,
        field_y: float = 100,
        sink_x: float = 50,
        sink_y: float = 175,
        p_ch: float = 0.05,
        initial_energy: float = 0.5,
        m: float = 0.0,            # advanced-node fraction (heterogeneity)
        a_mult: float = 2.0,       # advanced initial-energy multiplier
    ):
        self.n = n_nodes
        self.field_x = field_x
        self.field_y = field_y
        self.sink = Node(-1, sink_x, sink_y, energy=float('inf'))
        if not (0.0 < p_ch < 1.0):
            raise ValueError(f"p_ch must be in (0,1), got {p_ch}")
        if n_nodes < 1:
            raise ValueError(f"n_nodes must be >= 1, got {n_nodes}")
        if not (0.0 <= m <= 1.0):
            raise ValueError(f"m must be in [0,1], got {m}")
        self.p = p_ch
        self.round = 0
        self.alive_count = n_nodes
        self.history = []  # (round, alive, total_energy, pdr, avg_delay, packets_sent, packets_received)

        # Create nodes (heterogeneity-aware, mirrors ClusterChain-H / SEP / DEEC)
        n_adv = int(round(m * n_nodes))
        self.nodes = [
            Node(i, random.uniform(0, field_x), random.uniform(0, field_y),
                 a_mult * initial_energy if i < n_adv else initial_energy)
            for i in range(n_nodes)
        ]

    def _threshold(self, node: Node) -> float:
        """LEACH threshold T(n) = p / (1 - p * (r mod 1/p)) if n in G else 0"""
        epoch = max(1, int(round(1 / self.p)))
        if self.round - node.last_ch_round >= epoch:
            return self.p / (1 - self.p * (self.round % epoch))
        return 0.0

    def _select_cluster_heads(self):
        """Probabilistic CH selection"""
        for node in self.nodes:
            if node.alive and random.random() < self._threshold(node):
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = self.round
            else:
                node.is_ch = False

    def _form_clusters(self):
        """Non-CH nodes join nearest CH"""
        chs = [n for n in self.nodes if n.alive and n.is_ch]
        if not chs:
            # Fallback: make highest-energy node CH
            alive = [n for n in self.nodes if n.alive]
            if alive:
                max_node = max(alive, key=lambda n: n.energy)
                max_node.is_ch = True
                chs = [max_node]

        for node in self.nodes:
            if node.alive and not node.is_ch:
                nearest = min(chs, key=lambda ch: node.distance_to(ch))
                node.ch_id = nearest.id

    def _transmit_round(self) -> dict:
        """One round of data transmission. PDR = source nodes whose data reached
        the sink / total alive source nodes (consistent across all protocols)."""
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return {'tx_energy': 0, 'rx_energy': 0, 'packets_sent': 0,
                    'packets_received': 0, 'avg_delay': 0}

        sent = len(alive)
        delivered = {n.id for n in alive}
        by_id = {n.id: n for n in alive}
        total_tx = 0.0
        total_rx = 0.0
        delays = []

        # map cluster head -> member ids (for cascade invalidation)
        members = {}
        for n in alive:
            if not n.is_ch and n.ch_id is not None:
                members.setdefault(n.ch_id, []).append(n.id)

        # Non-CH nodes transmit to CH
        for node in alive:
            if node.is_ch or node.ch_id is None:
                continue
            ch = by_id.get(node.ch_id)
            if ch is None or not ch.alive:
                continue
            d = node.distance_to(ch)
            if not in_range(d):
                node.consume(tx_energy(d))
                delivered.discard(node.id)
                continue
            if node.consume(tx_energy(d)):
                delivered.discard(node.id)
                continue
            if ch.consume(rx_energy() + da_energy()):
                for m in members.get(ch.id, []):
                    delivered.discard(m)
                delivered.discard(ch.id)
                continue
            total_tx += tx_energy(d)
            total_rx += rx_energy() + da_energy()

        # CHs transmit aggregated data to sink
        for node in alive:
            if not node.is_ch:
                continue
            d = node.distance_to(self.sink)
            if node.consume(tx_energy(d)):
                for m in members.get(node.id, []):
                    delivered.discard(m)
                delivered.discard(node.id)
                continue
            total_tx += tx_energy(d)
            delays.append(1)

        return {
            'tx_energy': total_tx,
            'rx_energy': total_rx,
            'packets_sent': sent,
            'packets_received': len(delivered),
            'avg_delay': np.mean(delays) if delays else 0,
        }

    def step(self) -> dict:
        """Run one LEACH round"""
        self.round += 1
        self._select_cluster_heads()
        self._form_clusters()
        metrics = self._transmit_round()

        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = metrics['packets_received'] / max(1, metrics['packets_sent'])

        self.history.append((
            self.round,
            self.alive_count,
            metrics['tx_energy'] + metrics['rx_energy'],
            pdr,
            metrics['avg_delay'],
            metrics['packets_sent'],
            metrics['packets_received']
        ))
        return {
            'round': self.round,
            'alive': self.alive_count,
            'pdr': pdr,
            'delay': metrics['avg_delay'],
            'energy': metrics['tx_energy'] + metrics['rx_energy'],
        }

    def run(self, max_rounds: int = 2000) -> List[tuple]:
        """Run until all dead or max_rounds"""
        while self.alive_count > 0 and self.round < max_rounds:
            self.step()
        return self.history