"""Experimental Relay-Sink variant (static relay tier, no mobility).

The review's highest-upside-but-highest-proof-burden candidate is a mobile /
relay sink. To isolate the GEOMETRIC benefit from mobility accounting, we test
a STATIC relay-sink tier instead of a moving sink: fixed relay collection
points sit closer to the field than the off-field base station at (50,175).
Each chain's terminus jumps to its nearest relay instead of the far BS, which
is the same energy it would spend on the sink hop -- just over a shorter
distance. The relay then forwards to the BS.

Two honesty modes:
  relay_energy=None  -> UNLIMITED relay (infrastructure subsidy NOT charged):
                        shows the maximum geometric upside only.
  relay_energy=0.5  -> BUDGETED relay (per-relay battery == one node):
                        exposes whether the relay becomes a new bottleneck.

Fairness: the sensor-side energy (terminus -> relay) is charged exactly like
the baseline's terminus -> sink hop, so sensor LAST is a like-for-like
comparison. The relay -> BS forward hop is infrastructure and is tracked in
self.relay_energy separately, never folded into sensor energy. If a budgeted
relay's battery is exhausted, its chains fall back to direct terminus -> BS
(charged to the sensor, as baseline does).
"""
import numpy as np
from clusterchain_h import (
    ClusterChainH, partition_into_chains, build_refined_chain,
)
from energy import tx_energy, rx_energy, da_energy, in_range


class RelaySinkClusterChain(ClusterChainH):
    def __init__(self, *a, relay_positions=None, relay_energy=None, K=1, **kw):
        super().__init__(*a, **kw)
        # Default: two relays flanking the field, both far closer than the
        # off-field BS at (50,175). Tunable via relay_positions.
        self.relay_positions = relay_positions or [(50.0, 50.0), (50.0, 150.0)]
        self.relay_energy_budget = relay_energy
        self.relay_energy = [relay_energy for _ in self.relay_positions] \
            if relay_energy is not None else None
        self.relay_forward_total = 0.0
        self.relay_dead_round = None
        self.K = max(1, min(K, kw.get('n_nodes', 100)))

    def _nearest_relay(self, x, y):
        best_i, best_d = 0, float('inf')
        for i, (rx, ry) in enumerate(self.relay_positions):
            d = ((x - rx) ** 2 + (y - ry) ** 2) ** 0.5
            if d < best_d:
                best_d, best_i = d, i
        return best_i, best_d

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
                if c.chain_next is None:
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

            ridx, d_relay = self._nearest_relay(terminus.x, terminus.y)
            if terminus.consume(tx_energy(d_relay)):
                for node in ordered:
                    delivered.discard(node.id)
                continue
            total_tx += tx_energy(d_relay)

            (rx, ry) = self.relay_positions[ridx]
            d_bs = ((rx - self.sink.x) ** 2 + (ry - self.sink.y) ** 2) ** 0.5
            e_bs = tx_energy(d_bs)
            if self.relay_energy is not None:
                if self.relay_energy[ridx] >= e_bs:
                    self.relay_energy[ridx] -= e_bs
                    self.relay_forward_total += e_bs
                else:
                    # budget exhausted -> flag death once, then fallback
                    if self.relay_dead_round is None:
                        self.relay_dead_round = self.round
                    for node in ordered:
                        delivered.discard(node.id)
                    continue
            else:
                self.relay_forward_total += e_bs

            delays.append(max(1, len(ordered)) + 1)

        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def step(self):
        self.round += 1
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.alive_count = len(alive)

        k = max(1, min(self.K, self.alive_count))
        raw_chains = partition_into_chains(alive, k)
        chains = []
        for ch in raw_chains:
            sig = frozenset(id(n) for n in ch)
            cached = self._chain_store.get(sig)
            if cached is not None:
                chains.append(build_refined_chain(cached, self.sink,
                                                  rotate=self.rotate, refine=False))
            else:
                built = build_refined_chain(ch, self.sink,
                                            rotate=self.rotate, refine=True)
                self._chain_store[sig] = built
                chains.append(built)
        m = self._transmit_relay_multichain(chains)

        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = m['received'] / max(1, m['sent'])
        self.history.append((
            self.round, self.alive_count, m['tx'] + m['rx'], pdr,
            m['delay'], m['sent'], m['received'],
        ))
        # record relay battery state if budgeted
        if self.relay_energy is not None:
            self.history[-1] = self.history[-1] + (tuple(self.relay_energy),)
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr,
                'delay': m['delay'], 'energy': m['tx'] + m['rx']}


class RelayRotationClusterChain(RelaySinkClusterChain):
    """Budgeted relay tier with ROTATION: the relay role is not fixed to two
    nodes. Every `rotate_every` rounds, re-select the R highest-residual-energy
    alive nodes (within the relay zone, default the central band) as the new
    relays. This spreads the relay->BS infrastructure cost across many nodes so
    no single 0.5J relay dies at round 341 and collapses PDR.

    When rotate_every is None, behaves identically to the static tier (proves
    the rotation is what changes the result, not something else).

    Energy fairness is unchanged: the sensor-side terminus->relay hop is charged
    to the sensor exactly like the baseline's terminus->BS hop. The relay->BS
    forward is infrastructure, tracked in self.relay_forward_total, never folded
    into sensor energy. Each rotated-in relay starts with a fresh 0.5J budget.
    """

    def __init__(self, *a, relay_count=2, rotate_every=50, relay_zone=None,
                 relay_energy=0.5, **kw):
        # Start with placeholder positions; real ones set on first step.
        super().__init__(*a, relay_positions=[(50.0, 50.0)] * relay_count,
                         relay_energy=relay_energy, **kw)
        self.relay_count = relay_count
        self.rotate_every = rotate_every
        # Relay zone: central horizontal band; any alive node landing here is
        # eligible. Default band is the field's vertical middle third.
        self.relay_zone = relay_zone or (self.field_y * 0.3, self.field_y * 0.7)
        self._relay_epoch = 0
        self.relay_dead_round = None  # first round a relay budget is exhausted
        self.pdr_after_341 = []  # per-round PDR once round > 341 (probe window)

    def _select_relays(self):
        alive = [n for n in self.nodes if n.alive]
        zlo, zhi = self.relay_zone
        eligible = [n for n in alive if zlo <= n.y <= zhi]
        pool = eligible if eligible else alive
        # highest residual energy first
        chosen = sorted(pool, key=lambda n: n.energy, reverse=True)[:self.relay_count]
        self.relay_positions = [(n.x, n.y) for n in chosen]
        # fresh 0.5J budget for the rotated-in relays
        if self.relay_energy_budget is not None:
            self.relay_energy = [self.relay_energy_budget for _ in chosen]

    def step(self):
        # rotate relays at epoch boundaries
        if self.rotate_every is not None:
            epoch = (self.round + 1) // self.rotate_every
            if epoch != self._relay_epoch and self.alive_count > 0:
                self._relay_epoch = epoch
                self._select_relays()
        out = super().step()
        if self.round > 341:
            self.pdr_after_341.append(out.get('pdr', 0.0) if isinstance(out, dict) else 0.0)
        return out
