"""SEP Protocol Implementation (Smaragdakis et al. 2004)"""
import random
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE


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
    is_advanced: bool = False

    def distance_to(self, other: 'Node') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def consume(self, amount: float) -> bool:
        self.energy -= amount
        if self.energy <= 0:
            self.alive = False
            self.energy = 0
            return True
        return False


class SEP:
    def __init__(
        self,
        n_nodes: int = 100,
        field_x: float = 100,
        field_y: float = 100,
        sink_x: float = 50,
        sink_y: float = 175,
        initial_energy: float = 0.5,
        m: float = 0.1,
        a_mult: float = 2.0,
        p_opt: float = 0.1,
        **kwargs
    ):
        self.n = n_nodes
        self.field_x = field_x
        self.field_y = field_y
        self.sink = Node(-1, sink_x, sink_y, energy=float('inf'))
        self.m = m
        self.a_mult = a_mult
        self.p = p_opt
        self.round = 0
        self.alive_count = n_nodes
        self.history = []

        n_adv = int(m * n_nodes)
        self.nodes = [
            Node(i, random.uniform(0, field_x), random.uniform(0, field_y),
                 a_mult * initial_energy if i < n_adv else initial_energy,
                 is_advanced=(i < n_adv))
            for i in range(n_nodes)
        ]

    def _select_cluster_heads(self):
        # Standard SEP (Smaragdakis et al. 2004): with advanced fraction m and
        # EXTRA energy factor a (= a_mult - 1, since a_mult is the total-energy
        # multiplier, e.g. a_mult=2.0 -> a=1.0 for 2x-energy nodes):
        #   p_nrm = p_opt / (1 + a*m),  p_adv = p_opt * (1+a) / (1 + a*m).
        a = self.a_mult - 1.0
        denom = 1 + a * self.m
        p_n = self.p / denom
        p_a = self.p * (1 + a) / denom
        for node in self.nodes:
            node.is_ch = False
            if not node.alive:
                continue
            p_i = p_a if node.is_advanced else p_n
            if random.random() < p_i:
                node.is_ch = True
                node.rounds_as_ch += 1
                node.last_ch_round = self.round

    def _form_clusters(self):
        chs = [n for n in self.nodes if n.alive and n.is_ch]
        if not chs:
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

        members = {}
        for n in alive:
            if not n.is_ch and n.ch_id is not None:
                members.setdefault(n.ch_id, []).append(n.id)

        for node in alive:
            if node.is_ch or node.ch_id is None:
                continue
            ch = by_id.get(node.ch_id)
            if ch is None or not ch.alive:
                continue
            d = node.distance_to(ch)
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
        while self.alive_count > 0 and self.round < max_rounds:
            self.step()
        return self.history
