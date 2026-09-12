"""Aggregation-traffic robustness harness (notes section 6.4).

Data fusion compresses correlated reports, so every forwarded payload costs
a fraction of a full packet. This harness scales ALL payload charges
(tx/rx/da, every protocol uniformly) by alpha in (0, 1] to test whether the
CCH-K1 vs PEGASIS margin survives under fusion traffic.

This is a traffic-model sensitivity check, NOT a protocol mechanism: both
sides get the same alpha, so a surviving margin means the geometry/rotation
edge is real, not an artifact of the zero-compression traffic model.

Usage:
    with agg(0.7):
        ClusterChainH(...).run(...)
PAYLOAD_SCALE restores automatically, even on exception. Default 1.0 is the
published model, bit-identical (proven by tests/test_aggregation.py).
"""

from contextlib import contextmanager

import energy


@contextmanager
def agg(alpha):
    """Scale every payload charge by alpha for the block. Restores after."""
    if not 0 < alpha <= 1.0:
        raise ValueError(f'alpha must be in (0, 1], got {alpha}')
    prev = energy.PAYLOAD_SCALE
    energy.PAYLOAD_SCALE = alpha
    try:
        yield alpha
    finally:
        energy.PAYLOAD_SCALE = prev
