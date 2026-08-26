"""Generate round-by-round network topology animations for each protocol.

Each protocol exposes the same runtime contract:
    sim = Protocol()           # node placement uses the global random seed
    sim.step()                 # advance one round
    sim.nodes                  # list of node objects with x, y, energy, alive
    sim.alive_count            # number of alive nodes
    sim.round                  # current round

Topology is read straight off the node objects:
    LEACH       : node.is_ch, node.ch_id            (member -> cluster head -> sink)
    PEGASIS     : node.next_id, node.is_leader       (greedy chain -> sink)
    ClusterChain: node.is_ch, node.ch_id, node.chain_next, node.is_terminus

Frames are sampled every N rounds and assembled into a looping GIF so the
energy drain and topology evolution are visible without a 1200-frame file.
"""

import os
import io
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image

from leach import LEACH
from pegasis import PEGASIS
from clusterchain import ClusterChain
from clusterchain_h import ClusterChainH

SEED = 42
FIELD = (100, 100)
SINK = (50, 175)

# How many rounds to run and how often to snapshot a frame.
MAX_ROUNDS = 1200
SAMPLE_EVERY = 40


def _color(energy: float, initial: float) -> tuple:
    """Residual energy -> blue (full) to red (empty) gradient."""
    frac = max(0.0, min(1.0, energy / initial))
    return (1.0 - frac, 0.35, frac)


def _leach_edges(nodes):
    edges = []
    for n in nodes:
        if n.alive and n.ch_id is not None and not n.is_ch:
            edges.append((n.id, n.ch_id))
    for n in nodes:
        if n.alive and n.is_ch:
            edges.append((n.id, -1))
    return edges


def _pegasis_edges(nodes):
    edges = []
    for n in nodes:
        if n.alive and n.next_id is not None:
            edges.append((n.id, n.next_id))
    for n in nodes:
        if n.alive and n.is_leader:
            edges.append((n.id, -1))
    return edges


def _clusterchain_edges(nodes):
    edges = []
    for n in nodes:
        if n.alive and not n.is_ch and n.ch_id is not None:
            edges.append((n.id, n.ch_id))
    for n in nodes:
        if n.alive and n.is_ch and n.chain_next is not None:
            edges.append((n.id, n.chain_next))
    for n in nodes:
        if n.alive and n.is_terminus:
            edges.append((n.id, -1))
    return edges


def _clusterchain_h_edges(nodes):
    """Edges for ClusterChain-H (multichain mode shows all chains)."""
    edges = []
    for n in nodes:
        if n.alive and not n.is_ch and n.ch_id is not None:
            edges.append((n.id, n.ch_id))
    for n in nodes:
        if n.alive and n.chain_next is not None:
            edges.append((n.id, n.chain_next))
    for n in nodes:
        if n.alive and n.is_terminus:
            edges.append((n.id, -1))
    return edges


def _coord_lookup(sim, nid):
    if nid == -1:
        return SINK
    return sim.nodes[nid].x, sim.nodes[nid].y


def _render_frame(sim, protocol, initial_energy):
    heads = []  # red-ring cluster heads / leaders
    if protocol == "leach":
        edges = _leach_edges(sim.nodes)
        heads = [(n.x, n.y) for n in sim.nodes if n.alive and n.is_ch]
    elif protocol == "pegasis":
        edges = _pegasis_edges(sim.nodes)
        heads = [(n.x, n.y) for n in sim.nodes if n.alive and n.is_leader]
    elif protocol == "clusterchain_h":
        edges = _clusterchain_h_edges(sim.nodes)
        heads = [(n.x, n.y) for n in sim.nodes if n.alive and (n.is_ch or n.is_terminus)]
    else:
        edges = _clusterchain_edges(sim.nodes)
        heads = [(n.x, n.y) for n in sim.nodes if n.alive and n.is_ch]

    fig, ax = plt.subplots(figsize=(5, 6.2), dpi=110)
    ax.set_xlim(-10, FIELD[0] + 10)
    ax.set_ylim(-10, FIELD[1] + 90)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    segs, ecols = [], [(0.55, 0.55, 0.55, 0.35)] * 200
    for a, b in edges:
        segs.append([_coord_lookup(sim, a), _coord_lookup(sim, b)])
    if segs:
        ax.add_collection(LineCollection(segs, colors=ecols[: len(segs)],
                                        linewidths=0.8, zorder=1))

    xs = [n.x for n in sim.nodes if n.alive]
    ys = [n.y for n in sim.nodes if n.alive]
    cols = [_color(n.energy, initial_energy) for n in sim.nodes if n.alive]
    sizes = [70 if (getattr(n, "is_ch", False) or getattr(n, "is_leader", False))
             else 28 for n in sim.nodes if n.alive]
    ax.scatter(xs, ys, c=cols, s=sizes, edgecolors="black", linewidths=0.3,
               zorder=2)
    if heads:
        ax.scatter([p[0] for p in heads], [p[1] for p in heads],
                   facecolors="none", edgecolors="red", s=240,
                   linewidths=1.6, zorder=3)
    ax.scatter([SINK[0]], [SINK[1]], c="green", marker="s", s=120,
               edgecolors="black", linewidths=0.6, zorder=4)

    ax.set_title(f"{protocol.upper()}  |  round {sim.round}  |  "
                 f"alive {sim.alive_count}/100", fontsize=11)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def make_animation(protocol: str, outfile: str, max_rounds=MAX_ROUNDS,
                   sample_every=SAMPLE_EVERY, seed=SEED):
    random.seed(seed)
    if protocol == "leach":
        sim = LEACH()
    elif protocol == "pegasis":
        sim = PEGASIS()
    elif protocol == "clusterchain_h":
        # Use heterogeneous multichain mode for animation
        sim = ClusterChainH(mode="multichain", K=3, m=0.1, a_mult=2.0)
    else:
        sim = ClusterChain()
    initial_energy = getattr(sim, "initial_energy", 0.5)

    frames = []
    r = 0
    while sim.alive_count > 0 and r < max_rounds:
        sim.step()
        r += 1
        if r % sample_every == 0 or sim.alive_count == 0:
            frames.append(_render_frame(sim, protocol, initial_energy))

    imgs = [Image.open(io.BytesIO(b)).convert("RGB") for b in frames]
    imgs[0].save(outfile, save_all=True, append_images=imgs[1:],
                 duration=320, loop=0)
    print(f"{protocol:10s} -> {outfile}  ({len(imgs)} frames)")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("leach", "pegasis", "clusterchain", "clusterchain_h"):
        make_animation(name, os.path.join(here, f"anim_{name}.gif"))
