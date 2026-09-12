"""ClusterChainH with AODV-style local chain repair (hypothesis prototype).

Does NOT modify clusterchain_h.py. Subclasses ClusterChainH and overrides
only the chain-build section of step(): when a chain's membership changed by
exactly one dead node since the cached build, the dead node is spliced out of
the cached order and the chain re-linked (O(|chain|)) instead of a full
greedy + 2-opt / MST rebuild (O(|pool|^2)). Any other change falls back to the
baseline rebuild path, so worst case == baseline behavior.

Hypotheses (tested by eval_localrepair.py; 3 coupled seeds, N=100, K=1):
  H1 lifetime: LAST/FND within +/-3% of baseline.
  H2 mechanism: >=80% of post-death rebuilds replaced by repairs.
  H3 delivery: mean PDR equal to baseline (>=0.99, |delta|<=0.005).
Reject (keep baseline, file as negative evidence) if H1 or H3 fails.
"""

from clusterchain_h import (
    ClusterChainH,
    _relink_chain,
    build_refined_chain,
    partition_into_chains,
)


def try_local_repair(cached_order, alive_ids, sink, rotate=True):
    """Splice dead nodes out of a cached chain order.

    Returns the patched + relinked list when exactly one cached node died,
    else None (caller must full-rebuild). Only rewires chain_next /
    is_terminus on the surviving node objects.
    """
    alive_ids = set(alive_ids)
    dead = {n.id for n in cached_order} - alive_ids
    if len(dead) != 1:
        return None
    patched = [n for n in cached_order if n.id in alive_ids]
    if not patched:
        return None
    return _relink_chain(patched, sink, rotate=rotate)


class ClusterChainH_LR(ClusterChainH):
    """ClusterChainH with local repair. History wire format identical."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_repairs = 0
        self.n_rebuilds = 0

    def _repair_or_rebuild(self, ch, sink):
        sig = frozenset(n.id for n in ch)
        cached = self._chain_store.get(sig)
        if cached is not None:
            return build_refined_chain(
                cached, sink, rotate=self.rotate, refine=False)
        alive_ids = {n.id for n in ch}
        for old_sig, old_chain in list(self._chain_store.items()):
            if len(old_sig) == len(sig) + 1 and sig < old_sig:
                patched = try_local_repair(
                    list(old_chain), alive_ids, sink, self.rotate)
                if patched is not None:
                    self._chain_store[sig] = patched
                    self.n_repairs += 1
                    return patched
        built = build_refined_chain(ch, sink, rotate=self.rotate, refine=True)
        self._chain_store[sig] = built
        self.n_rebuilds += 1
        return built

    def step(self):
        # Mirrored from ClusterChainH.step; the ONLY diff is the chain-build
        # block routing through _repair_or_rebuild. Clustered mode delegates
        # to baseline untouched (no chain cache there to repair).
        if self.mode == 'clustered':
            return super().step()
        self.round += 1
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            self.history.append((self.round, 0, 0, 0, 0, 0, 0))
            return {}
        self.alive_count = len(alive)

        mode = self.mode
        if mode == 'adaptive':
            mode = 'multichain'
            k = 1
        else:
            k = self.K

        k = max(1, min(k, self.alive_count))
        if mode == 'relay' and self.rotate_every is not None:
            epoch = (self.round + 1) // self.rotate_every
            if epoch != self._relay_epoch and self.alive_count > 0:
                self._relay_epoch = epoch
                self._select_relays()
        raw_chains = partition_into_chains(alive, k)
        chains = [self._repair_or_rebuild(ch, self.sink) for ch in raw_chains]
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
