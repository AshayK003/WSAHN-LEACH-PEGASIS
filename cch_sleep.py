"""ClusterChainH with rotating sleep subset (hypothesis prototype).

Baseline files untouched. Subclass overrides the round driver for multichain
mode: each round the top-f alive nodes by the baseline election score stay
awake and form the chain(s); the rest sleep at SLEEP_FRAC x rx per round.
Awake nodes pay one extra rx as SYNC schedule cost, charged only when f < 1.0
-- so f=1.0 is bit-identical to baseline (proven by tests/test_sleep.py).

Honesty notes: the sim models no sensing coverage, so sleepers not sensing
is free in-sim. Guardrails: (1) energy-per-delivered-report is a co-gate in
eval_sleep.py so reduced sensing volume cannot masquerade as efficiency;
(2) the density assumption (neighbors cover sleepers) is stated, not shown.
"""

from energy import in_range, rx_energy, tx_energy, da_energy
from clusterchain_h import (
    ClusterChainH,
    build_refined_chain,
    partition_into_chains,
)


class ClusterChainH_SLP(ClusterChainH):
    SLEEP_FRAC = 0.05  # sleeper idle burn, fraction of one rx per round

    def __init__(self, *args, awake_frac=1.0, **kwargs):
        if not 0 < awake_frac <= 1.0:
            raise ValueError(f'awake_frac must be in (0, 1], got {awake_frac}')
        super().__init__(*args, **kwargs)
        self.awake_frac = awake_frac

    def _select_awake(self, alive):
        if self.awake_frac >= 1.0:
            return list(alive)
        self._elect_heads(len(alive))  # baseline scoring over all alive
        for n in self.nodes:
            n.is_ch = False
            n.ch_id = None
        k = max(1, round(self.awake_frac * len(alive)))
        return sorted(alive, key=lambda n: n.score, reverse=True)[:k]

    def _transmit_awake(self, chains, awake):
        # Line-mirror of ClusterChainH._transmit_multichain with the awake
        # subset in place of alive. Identical when awake == alive.
        by_id = {n.id: n for n in awake}
        sent = len(awake)
        delivered = {n.id for n in awake}
        total_tx = 0.0
        total_rx = 0.0
        delays = []
        for chain in chains:
            broken = False
            ordered = [c for c in chain
                       if c.chain_next is not None or c.is_terminus]
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
                    for node in ordered:
                        delivered.discard(node.id)
                else:
                    total_tx += tx_energy(d)
                    delays.append(max(1, len(ordered)))
        return self._pack(sent, delivered, total_tx, total_rx, delays)

    def step(self):
        if self.mode != 'multichain':
            return super().step()
        self.round += 1
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.alive_count = len(alive)
        idle_e = 0.0
        sync_e = 0.0
        if self.awake_frac < 1.0:
            awake_ids = {n.id for n in self._select_awake(alive)}
            for n in alive:
                if n.id not in awake_ids:
                    n.consume(self.SLEEP_FRAC * rx_energy())
                    idle_e += self.SLEEP_FRAC * rx_energy()
            awake = [n for n in self.nodes if n.alive and n.id in awake_ids]
            for n in awake:
                n.consume(rx_energy())
                sync_e += rx_energy()
            awake = [n for n in awake if n.alive]
            if not awake:
                self.alive_count = sum(1 for n in self.nodes if n.alive)
                self.history.append((self.round, self.alive_count,
                                     idle_e + sync_e, 0.0, 0.0, 0, 0))
                return {'round': self.round, 'alive': self.alive_count,
                        'pdr': 0.0, 'delay': 0.0,
                        'energy': idle_e + sync_e}
        else:
            awake = alive

        k = max(1, min(self.K, len(awake)))
        raw_chains = partition_into_chains(awake, k)
        chains = []
        for ch in raw_chains:
            sig = frozenset(n.id for n in ch)
            cached = self._chain_store.get(sig)
            if cached is not None:
                chains.append(build_refined_chain(cached, self.sink,
                                                  rotate=self.rotate,
                                                  refine=False))
            else:
                built = build_refined_chain(ch, self.sink,
                                            rotate=self.rotate, refine=True)
                self._chain_store[sig] = built
                chains.append(built)
        m = self._transmit_awake(chains, awake)

        self.alive_count = sum(1 for n in self.nodes if n.alive)
        pdr = m['received'] / max(1, m['sent'])
        n_adv = sum(1 for n in self.nodes if n.alive and n.is_advanced)
        n_norm = self.alive_count - n_adv
        self.class_history.append((self.round, n_adv, n_norm))
        self.history.append((
            self.round, self.alive_count, m['tx'] + m['rx'] + idle_e + sync_e,
            pdr, m['delay'], m['sent'], m['received'],
        ))
        return {'round': self.round, 'alive': self.alive_count, 'pdr': pdr,
                'delay': m['delay'],
                'energy': m['tx'] + m['rx'] + idle_e + sync_e}
