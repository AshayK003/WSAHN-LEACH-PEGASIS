"""PEGASIS Protocol Implementation"""
import random
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from energy import tx_energy, rx_energy, da_energy, PACKET_SIZE


@dataclass
class PegNode:
    id: int
    x: float
    y: float
    energy: float = 0.5
    alive: bool = True
    next_id: Optional[int] = None  # next node in chain
    is_leader: bool = False
    rounds_as_leader: int = 0

    def distance_to(self, other: 'PegNode') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def consume(self, amount: float) -> bool:
        self.energy -= amount
        if self.energy <= 0:
            self.alive = False
            self.energy = 0
            return True
        return False


class PEGASIS:
    def __init__(
        self,
        n_nodes: int = 100,
        field_x: float = 100,
        field_y: float = 100,
        sink_x: float = 50,
        sink_y: float = 175,
        initial_energy: float = 0.5,
    ):
        self.n = n_nodes
        self.field_x = field_x
        self.field_y = field_y
        self.sink = PegNode(-1, sink_x, sink_y, energy=float('inf'))
        self.round = 0
        self.alive_count = n_nodes
        self.history = []  # (round, alive, total_energy, pdr, avg_delay, packets_sent, packets_received)

        # Create nodes
        self.nodes = [
            PegNode(i, random.uniform(0, field_x), random.uniform(0, field_y), initial_energy)
            for i in range(n_nodes)
        ]

        self._build_chain()

    def _build_chain(self):
        """Greedy chain formation: each node connects to nearest alive neighbor"""
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return

        # Start from random node
        unvisited = set(n.id for n in alive)
        chain = []
        current = random.choice(alive)
        chain.append(current)
        unvisited.remove(current.id)

        # Greedy nearest neighbor
        while unvisited:
            nearest = min(
                (n for n in alive if n.id in unvisited),
                key=lambda n: current.distance_to(n)
            )
            current.next_id = nearest.id
            chain.append(nearest)
            unvisited.remove(nearest.id)
            current = nearest

        # Last node is leader (transmits to sink)
        chain[-1].is_leader = True
        chain[-1].rounds_as_leader += 1

    def _rebuild_chain(self):
        """Rebuild chain after node deaths, select new leader"""
        for n in self.nodes:
            n.next_id = None
            n.is_leader = False
        self._build_chain()

    def _transmit_round(self) -> dict:
        """One round: data flows along chain to leader, leader to sink.
        PDR = source nodes whose data reached the sink / total alive nodes
        (consistent across all protocols, unlike the original per-hop count)."""
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return {'tx_energy': 0, 'rx_energy': 0, 'packets_sent': 0,
                    'packets_received': 0, 'avg_delay': 0}

        sent = len(alive)
        delivered = {n.id for n in alive}
        total_tx = 0.0
        total_rx = 0.0
        delays = []

        # Each alive node sends to next in chain; cascade: if any hop dies,
        # everything downstream of it (and the node itself) is lost.
        for node in alive:
            if node.next_id is None:  # leader
                continue
            next_node = next((n for n in alive if n.id == node.next_id), None)
            if next_node is None or not next_node.alive:
                # cannot forward -> node's own data and any still upstream is lost
                delivered.discard(node.id)
                continue
            d = node.distance_to(next_node)
            if node.consume(tx_energy(d)):
                delivered.discard(node.id)
                continue
            if next_node.consume(rx_energy() + da_energy()):
                delivered.discard(next_node.id)
                continue
            total_tx += tx_energy(d)
            total_rx += rx_energy() + da_energy()

        # Leader transmits fused data to sink
        leader = next((n for n in alive if n.is_leader), None)
        if leader:
            d = leader.distance_to(self.sink)
            if leader.consume(tx_energy(d)):
                delivered.clear()
            else:
                total_tx += tx_energy(d)
                delays.append(len(alive))  # delay ~ chain length

        return {
            'tx_energy': total_tx,
            'rx_energy': total_rx,
            'packets_sent': sent,
            'packets_received': len(delivered),
            'avg_delay': np.mean(delays) if delays else 0,
        }

    def step(self) -> dict:
        """Run one PEGASIS round"""
        self.round += 1

        # Rebuild chain every round (standard PEGASIS)
        self._rebuild_chain()

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