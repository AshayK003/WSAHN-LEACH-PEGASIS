"""Animation: cluster/chain evolution GIF"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from leach import LEACH
from pegasis import PEGASIS


def animate_leach(n_nodes=100, field_x=100, field_y=100, sink_x=50, sink_y=175, max_frames=50, output='leach_anim.gif'):
    """Generate LEACH cluster evolution animation"""
    sim = LEACH(n_nodes=n_nodes, field_x=field_x, field_y=field_y, sink_x=sink_x, sink_y=sink_y)
    
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-10, field_x + 10)
    ax.set_ylim(-10, field_y + 10)
    ax.set_aspect('equal')
    ax.set_title('LEACH Cluster Evolution')
    ax.grid(True, alpha=0.3)
    
    # Sink marker
    ax.plot(sink_x, sink_y, 'k^', markersize=15, label='Sink')
    
    scatter = ax.scatter([], [], c=[], s=50, cmap='RdYlGn', vmin=0, vmax=0.5)
    ch_scatter = ax.scatter([], [], c='red', s=200, marker='*', label='Cluster Heads')
    lines = []
    
    def update(frame):
        nonlocal lines
        for line in lines:
            line.remove()
        lines = []
        
        if frame > 0:
            sim.step()
        
        alive_nodes = [n for n in sim.nodes if n.alive]
        if not alive_nodes:
            return scatter, ch_scatter
        
        xs = [n.x for n in alive_nodes]
        ys = [n.y for n in alive_nodes]
        energies = [n.energy for n in alive_nodes]
        scatter.set_offsets(np.c_[xs, ys])
        scatter.set_array(np.array(energies))
        
        chs = [n for n in alive_nodes if n.is_ch]
        if chs:
            ch_xs = [n.x for n in chs]
            ch_ys = [n.y for n in chs]
            ch_scatter.set_offsets(np.c_[ch_xs, ch_ys])
            
            # Draw cluster lines
            for ch in chs:
                members = [n for n in alive_nodes if n.ch_id == ch.id and not n.is_ch]
                for m in members:
                    line, = ax.plot([m.x, ch.x], [m.y, ch.y], 'b-', alpha=0.3, linewidth=0.5)
                    lines.append(line)
                # CH to sink
                line, = ax.plot([ch.x, sink_x], [ch.y, sink_y], 'r--', alpha=0.5, linewidth=1)
                lines.append(line)
        
        ax.set_title(f'LEACH - Round {sim.round} | Alive: {sim.alive_count}')
        return scatter, ch_scatter
    
    anim = animation.FuncAnimation(fig, update, frames=max_frames, interval=300, blit=False)
    anim.save(output, writer='pillow', fps=3)
    plt.close()
    print(f"Saved {output}")


def animate_pegasis(n_nodes=100, field_x=100, field_y=100, sink_x=50, sink_y=175, max_frames=50, output='pegasis_anim.gif'):
    """Generate PEGASIS chain evolution animation"""
    sim = PEGASIS(n_nodes=n_nodes, field_x=field_x, field_y=field_y, sink_x=sink_x, sink_y=sink_y)
    
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-10, field_x + 10)
    ax.set_ylim(-10, field_y + 10)
    ax.set_aspect('equal')
    ax.set_title('PEGASIS Chain Evolution')
    ax.grid(True, alpha=0.3)
    
    ax.plot(sink_x, sink_y, 'k^', markersize=15, label='Sink')
    
    scatter = ax.scatter([], [], c=[], s=50, cmap='RdYlGn', vmin=0, vmax=0.5)
    leader_scatter = ax.scatter([], [], c='red', s=200, marker='*', label='Leader')
    lines = []
    
    def update(frame):
        nonlocal lines
        for line in lines:
            line.remove()
        lines = []
        
        if frame > 0:
            sim.step()
        
        alive_nodes = [n for n in sim.nodes if n.alive]
        if not alive_nodes:
            return scatter, leader_scatter
        
        xs = [n.x for n in alive_nodes]
        ys = [n.y for n in alive_nodes]
        energies = [n.energy for n in alive_nodes]
        scatter.set_offsets(np.c_[xs, ys])
        scatter.set_array(np.array(energies))
        
        leader = next((n for n in alive_nodes if n.is_leader), None)
        if leader:
            leader_scatter.set_offsets(np.c_[[leader.x], [leader.y]])
            
            # Draw chain
            node_map = {n.id: n for n in alive_nodes}
            visited = set()
            for n in alive_nodes:
                if n.id in visited:
                    continue
                current = n
                path = [current]
                visited.add(current.id)
                while current.next_id and current.next_id in node_map:
                    current = node_map[current.next_id]
                    if current.id in visited:
                        break
                    path.append(current)
                    visited.add(current.id)
                
                if len(path) > 1:
                    px = [p.x for p in path]
                    py = [p.y for p in path]
                    line, = ax.plot(px, py, 'g-', alpha=0.6, linewidth=1.5)
                    lines.append(line)
            
            # Leader to sink
            if leader:
                line, = ax.plot([leader.x, sink_x], [leader.y, sink_y], 'r--', alpha=0.7, linewidth=2)
                lines.append(line)
        
        ax.set_title(f'PEGASIS - Round {sim.round} | Alive: {sim.alive_count}')
        return scatter, leader_scatter
    
    anim = animation.FuncAnimation(fig, update, frames=max_frames, interval=300, blit=False)
    anim.save(output, writer='pillow', fps=3)
    plt.close()
    print(f"Saved {output}")


if __name__ == '__main__':
    animate_leach(max_frames=50, output='leach_anim.gif')
    animate_pegasis(max_frames=50, output='pegasis_anim.gif')