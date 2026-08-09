"""Additional visual demonstrations"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
from leach import LEACH
from pegasis import PEGASIS


def energy_heatmap_evolution(n_nodes=100, field_x=100, field_y=100, output='energy_heatmap.gif'):
    """Energy depletion heatmap over time"""
    sim = LEACH(n_nodes=n_nodes, field_x=field_x, field_y=field_y)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(-5, field_x + 5)
    ax.set_ylim(-5, field_y + 5)
    ax.set_aspect('equal')
    ax.set_title('LEACH Energy Depletion Heatmap')
    
    # Create grid for interpolation
    xi = np.linspace(0, field_x, 50)
    yi = np.linspace(0, field_y, 50)
    Xi, Yi = np.meshgrid(xi, yi)
    
    def update(frame):
        ax.clear()
        ax.set_xlim(-5, field_x + 5)
        ax.set_ylim(-5, field_y + 5)
        ax.set_aspect('equal')
        
        if frame > 0:
            sim.step()
        
        alive = [n for n in sim.nodes if n.alive]
        if not alive:
            return
        
        xs = np.array([n.x for n in alive])
        ys = np.array([n.y for n in alive])
        energies = np.array([n.energy for n in alive])
        
        # Interpolate energy field
        from scipy.interpolate import griddata
        try:
            Zi = griddata((xs, ys), energies, (Xi, Yi), method='cubic', fill_value=0)
            im = ax.contourf(Xi, Yi, Zi, levels=20, cmap='RdYlGn', vmin=0, vmax=0.5, alpha=0.8)
            plt.colorbar(im, ax=ax, label='Energy (J)')
        except:
            pass
        
        # Plot nodes
        ax.scatter(xs, ys, c=energies, s=50, cmap='RdYlGn', vmin=0, vmax=0.5, edgecolors='k', linewidth=0.5)
        
        # Sink
        ax.plot(50, 175, 'k^', markersize=15, label='Sink')
        
        ax.set_title(f'Round {sim.round} | Alive: {sim.alive_count} | Total Energy: {sum(energies):.2f} J')
        ax.legend()
    
    anim = animation.FuncAnimation(fig, update, frames=80, interval=200, blit=False)
    anim.save(output, writer='pillow', fps=5)
    plt.close()
    print(f"Saved {output}")


def side_by_side_comparison(n_nodes=100, max_frames=60, output='side_by_side.gif'):
    """LEACH and PEGASIS running side by side"""
    leach = LEACH(n_nodes=n_nodes)
    pegasis = PEGASIS(n_nodes=n_nodes)
    
    fig = plt.figure(figsize=(16, 7))
    gs = GridSpec(1, 2, figure=fig)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    
    for ax, title in [(ax1, 'LEACH'), (ax2, 'PEGASIS')]:
        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 180)
        ax.set_aspect('equal')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.plot(50, 175, 'k^', markersize=12)
    
    def update(frame):
        ax1.clear()
        ax2.clear()
        
        for ax, title in [(ax1, 'LEACH'), (ax2, 'PEGASIS')]:
            ax.set_xlim(-5, 105)
            ax.set_ylim(-5, 180)
            ax.set_aspect('equal')
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            ax.plot(50, 175, 'k^', markersize=12)
        
        if frame > 0:
            leach.step()
            pegasis.step()
        
        # LEACH
        alive_l = [n for n in leach.nodes if n.alive]
        if alive_l:
            xs_l = [n.x for n in alive_l]
            ys_l = [n.y for n in alive_l]
            es_l = [n.energy for n in alive_l]
            chs_l = [n for n in alive_l if n.is_ch]
            
            ax1.scatter(xs_l, ys_l, c=es_l, s=40, cmap='RdYlGn', vmin=0, vmax=0.5, edgecolors='k', linewidth=0.3)
            if chs_l:
                ch_xs = [n.x for n in chs_l]
                ch_ys = [n.y for n in chs_l]
                ax1.scatter(ch_xs, ch_ys, c='red', s=150, marker='*', edgecolors='k')
                for ch in chs_l:
                    members = [n for n in alive_l if n.ch_id == ch.id and not n.is_ch]
                    for m in members:
                        ax1.plot([m.x, ch.x], [m.y, ch.y], 'b-', alpha=0.2, linewidth=0.3)
                    ax1.plot([ch.x, 50], [ch.y, 175], 'r--', alpha=0.4, linewidth=0.5)
        
        # PEGASIS
        alive_p = [n for n in pegasis.nodes if n.alive]
        if alive_p:
            xs_p = [n.x for n in alive_p]
            ys_p = [n.y for n in alive_p]
            es_p = [n.energy for n in alive_p]
            leader = next((n for n in alive_p if n.is_leader), None)
            
            ax2.scatter(xs_p, ys_p, c=es_p, s=40, cmap='RdYlGn', vmin=0, vmax=0.5, edgecolors='k', linewidth=0.3)
            if leader:
                ax2.scatter([leader.x], [leader.y], c='red', s=150, marker='*', edgecolors='k')
                # Draw chain
                node_map = {n.id: n for n in alive_p}
                visited = set()
                for n in alive_p:
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
                        ax2.plot(px, py, 'g-', alpha=0.5, linewidth=1)
                ax2.plot([leader.x, 50], [leader.y, 175], 'r--', alpha=0.6, linewidth=1.5)
        
        ax1.set_title(f'LEACH - Round {leach.round} | Alive: {leach.alive_count}')
        ax2.set_title(f'PEGASIS - Round {pegasis.round} | Alive: {pegasis.alive_count}')
    
    anim = animation.FuncAnimation(fig, update, frames=max_frames, interval=300, blit=False)
    anim.save(output, writer='pillow', fps=3)
    plt.close()
    print(f"Saved {output}")


def metrics_dashboard(n_nodes=100, max_rounds=2000, output='dashboard.png'):
    """Static dashboard with all metrics"""
    leach = LEACH(n_nodes=n_nodes)
    leach.run(max_rounds)
    
    pegasis = PEGASIS(n_nodes=n_nodes)
    pegasis.run(max_rounds)
    
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(3, 3, figure=fig)
    
    # Extract data
    l_rounds = [h[0] for h in leach.history]
    l_alive = [h[1] for h in leach.history]
    l_energy = [h[2] for h in leach.history]
    l_pdr = [h[3] for h in leach.history]
    l_delay = [h[4] for h in leach.history]
    
    p_rounds = [h[0] for h in pegasis.history]
    p_alive = [h[1] for h in pegasis.history]
    p_energy = [h[2] for h in pegasis.history]
    p_pdr = [h[3] for h in pegasis.history]
    p_delay = [h[4] for h in pegasis.history]
    
    # 1. Network Lifetime (large)
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.plot(l_rounds, l_alive, 'b-', label='LEACH', linewidth=2)
    ax1.plot(p_rounds, p_alive, 'r-', label='PEGASIS', linewidth=2)
    ax1.fill_between(l_rounds, 0, l_alive, alpha=0.1, color='blue')
    ax1.fill_between(p_rounds, 0, p_alive, alpha=0.1, color='red')
    ax1.set_xlabel('Round')
    ax1.set_ylabel('Alive Nodes')
    ax1.set_title('Network Lifetime Comparison')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Energy per Round
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.plot(l_rounds, l_energy, 'b-', label='LEACH', linewidth=1.5)
    ax2.plot(p_rounds, p_energy, 'r-', label='PEGASIS', linewidth=1.5)
    ax2.set_xlabel('Round')
    ax2.set_ylabel('Energy (J)')
    ax2.set_title('Energy/Round')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. PDR
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(l_rounds, l_pdr, 'b-', label='LEACH', linewidth=1.5)
    ax3.plot(p_rounds, p_pdr, 'r-', label='PEGASIS', linewidth=1.5)
    ax3.set_xlabel('Round')
    ax3.set_ylabel('PDR')
    ax3.set_title('Packet Delivery Ratio')
    ax3.set_ylim(0, 1.05)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Delay
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(l_rounds, l_delay, 'b-', label='LEACH', linewidth=1.5)
    ax4.plot(p_rounds, p_delay, 'r-', label='PEGASIS', linewidth=1.5)
    ax4.set_xlabel('Round')
    ax4.set_ylabel('Delay (hops)')
    ax4.set_title('Average Delay')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. Cumulative Energy
    ax5 = fig.add_subplot(gs[1, 2])
    l_cum = np.cumsum(l_energy)
    p_cum = np.cumsum(p_energy)
    ax5.plot(l_rounds, l_cum, 'b-', label='LEACH', linewidth=1.5)
    ax5.plot(p_rounds, p_cum, 'r-', label='PEGASIS', linewidth=1.5)
    ax5.set_xlabel('Round')
    ax5.set_ylabel('Cumulative Energy (J)')
    ax5.set_title('Total Energy Consumed')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 6. Alive Nodes Distribution (histogram of death rounds)
    ax6 = fig.add_subplot(gs[2, 0])
    l_deaths = [n.round_of_death if hasattr(n, 'round_of_death') else leach.history[-1][0] for n in leach.nodes]
    p_deaths = [n.round_of_death if hasattr(n, 'round_of_death') else pegasis.history[-1][0] for n in pegasis.nodes]
    # Calculate from history
    l_death_rounds = []
    for i in range(1, len(leach.history)):
        dead = leach.history[i-1][1] - leach.history[i][1]
        l_death_rounds.extend([leach.history[i][0]] * max(0, dead))
    p_death_rounds = []
    for i in range(1, len(pegasis.history)):
        dead = pegasis.history[i-1][1] - pegasis.history[i][1]
        p_death_rounds.extend([pegasis.history[i][0]] * max(0, dead))
    
    ax6.hist(l_death_rounds, bins=30, alpha=0.5, label='LEACH', color='blue', density=True)
    ax6.hist(p_death_rounds, bins=30, alpha=0.5, label='PEGASIS', color='red', density=True)
    ax6.set_xlabel('Round of Death')
    ax6.set_ylabel('Density')
    ax6.set_title('Node Death Distribution')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    # 7. Key Metrics Table
    ax7 = fig.add_subplot(gs[2, 1:])
    ax7.axis('off')
    
    # Calculate summary stats
    leach_lifetime = len(leach.history)
    pegasis_lifetime = len(pegasis.history)
    leach_half = next((r for r, a, *_ in leach.history if a <= n_nodes/2), leach_lifetime)
    pegasis_half = next((r for r, a, *_ in pegasis.history if a <= n_nodes/2), pegasis_lifetime)
    leach_avg_pdr = np.mean(l_pdr)
    pegasis_avg_pdr = np.mean(p_pdr)
    leach_avg_delay = np.mean(l_delay)
    pegasis_avg_delay = np.mean(p_delay)
    leach_total_energy = sum(l_energy)
    pegasis_total_energy = sum(p_energy)
    
    table_data = [
        ['Metric', 'LEACH', 'PEGASIS', 'Winner'],
        ['Network Lifetime (rounds)', f'{leach_lifetime}', f'{pegasis_lifetime}', 'PEGASIS' if pegasis_lifetime > leach_lifetime else 'LEACH'],
        ['50% Nodes Dead (round)', f'{leach_half}', f'{pegasis_half}', 'PEGASIS' if pegasis_half > leach_half else 'LEACH'],
        ['Avg PDR', f'{leach_avg_pdr:.3f}', f'{pegasis_avg_pdr:.3f}', 'LEACH' if leach_avg_pdr > pegasis_avg_pdr else 'PEGASIS'],
        ['Avg Delay (hops)', f'{leach_avg_delay:.1f}', f'{pegasis_avg_delay:.1f}', 'LEACH' if leach_avg_delay < pegasis_avg_delay else 'PEGASIS'],
        ['Total Energy (J)', f'{leach_total_energy:.2f}', f'{pegasis_total_energy:.2f}', 'PEGASIS' if pegasis_total_energy < leach_total_energy else 'LEACH'],
        ['Energy Efficiency', f'{leach_lifetime/leach_total_energy:.1f}', f'{pegasis_lifetime/pegasis_total_energy:.1f}', 'PEGASIS' if (pegasis_lifetime/pegasis_total_energy) > (leach_lifetime/leach_total_energy) else 'LEACH'],
    ]
    
    table = ax7.table(cellText=table_data, cellLoc='center', loc='center', colWidths=[0.3, 0.2, 0.2, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    for i in range(len(table_data)):
        for j in range(4):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor('#4CAF50')
                cell.set_text_props(weight='bold', color='white')
            elif j == 3:
                if cell.get_text().get_text() == 'LEACH':
                    cell.set_facecolor('#E3F2FD')
                else:
                    cell.set_facecolor('#FFEBEE')
    
    ax7.set_title('Performance Summary', pad=20, fontsize=14, fontweight='bold')
    
    plt.suptitle('LEACH vs PEGASIS - Comprehensive Dashboard', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved {output}")


def node_death_timeline(n_nodes=100, output='death_timeline.png'):
    """Visual timeline of node deaths"""
    leach = LEACH(n_nodes=n_nodes)
    leach.run(2000)
    
    pegasis = PEGASIS(n_nodes=n_nodes)
    pegasis.run(2000)
    
    # Calculate death rounds per node
    def get_death_rounds(history):
        deaths = []
        prev_alive = history[0][1]
        for r, alive, *_ in history[1:]:
            dead = prev_alive - alive
            deaths.extend([r] * max(0, dead))
            prev_alive = alive
        return deaths
    
    l_deaths = get_death_rounds(leach.history)
    p_deaths = get_death_rounds(pegasis.history)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # LEACH
    ax1.hist(l_deaths, bins=50, color='blue', alpha=0.7, edgecolor='black', linewidth=0.3)
    ax1.axvline(np.mean(l_deaths), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(l_deaths):.0f}')
    ax1.axvline(np.median(l_deaths), color='orange', linestyle='--', linewidth=2, label=f'Median: {np.median(l_deaths):.0f}')
    ax1.set_ylabel('Nodes Died')
    ax1.set_title('LEACH - Node Death Timeline')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # PEGASIS
    ax2.hist(p_deaths, bins=50, color='red', alpha=0.7, edgecolor='black', linewidth=0.3)
    ax2.axvline(np.mean(p_deaths), color='blue', linestyle='--', linewidth=2, label=f'Mean: {np.mean(p_deaths):.0f}')
    ax2.axvline(np.median(p_deaths), color='orange', linestyle='--', linewidth=2, label=f'Median: {np.median(p_deaths):.0f}')
    ax2.set_xlabel('Round')
    ax2.set_ylabel('Nodes Died')
    ax2.set_title('PEGASIS - Node Death Timeline')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle('Node Death Distribution Over Time', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"Saved {output}")


def packet_flow_snapshot(n_nodes=50, output='packet_flow.png'):
    """Single snapshot showing packet flow paths"""
    leach = LEACH(n_nodes=n_nodes)
    leach.run(10)
    
    pegasis = PEGASIS(n_nodes=n_nodes)
    pegasis.run(10)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    for ax, sim, title in [(ax1, leach, 'LEACH - Packet Flow (Round 10)'), (ax2, pegasis, 'PEGASIS - Packet Flow (Round 10)')]:
        ax.set_xlim(-5, 105)
        ax.set_ylim(-5, 180)
        ax.set_aspect('equal')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.plot(50, 175, 'k^', markersize=15, label='Sink')
        
        alive = [n for n in sim.nodes if n.alive]
        xs = [n.x for n in alive]
        ys = [n.y for n in alive]
        energies = [n.energy for n in alive]
        
        scatter = ax.scatter(xs, ys, c=energies, s=60, cmap='RdYlGn', vmin=0, vmax=0.5, edgecolors='k', linewidth=0.5)
        plt.colorbar(scatter, ax=ax, label='Energy (J)')
        
        if isinstance(sim, LEACH):
            chs = [n for n in alive if n.is_ch]
            if chs:
                ch_xs = [n.x for n in chs]
                ch_ys = [n.y for n in chs]
                ax.scatter(ch_xs, ch_ys, c='red', s=200, marker='*', edgecolors='k', label='Cluster Heads')
                for ch in chs:
                    members = [n for n in alive if n.ch_id == ch.id and not n.is_ch]
                    for m in members:
                        ax.annotate('', xy=(ch.x, ch.y), xytext=(m.x, m.y),
                                  arrowprops=dict(arrowstyle='->', color='blue', alpha=0.4, lw=1))
                    ax.annotate('', xy=(50, 175), xytext=(ch.x, ch.y),
                              arrowprops=dict(arrowstyle='->', color='red', alpha=0.6, lw=2))
        
        else:
            leader = next((n for n in alive if n.is_leader), None)
            if leader:
                ax.scatter([leader.x], [leader.y], c='red', s=200, marker='*', edgecolors='k', label='Leader')
                node_map = {n.id: n for n in alive}
                visited = set()
                for n in alive:
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
                        for i in range(len(path)-1):
                            ax.annotate('', xy=(path[i+1].x, path[i+1].y), xytext=(path[i].x, path[i].y),
                                      arrowprops=dict(arrowstyle='->', color='green', alpha=0.5, lw=1.5))
                ax.annotate('', xy=(50, 175), xytext=(leader.x, leader.y),
                          arrowprops=dict(arrowstyle='->', color='red', alpha=0.8, lw=3))
        
        ax.legend()
    
    plt.tight_layout()
    plt.savefig(output, dpi=150)
    plt.close()
    print(f"Saved {output}")


if __name__ == '__main__':
    print("Generating additional visualizations...")
    energy_heatmap_evolution(output='energy_heatmap.gif')
    side_by_side_comparison(max_frames=50, output='side_by_side.gif')
    metrics_dashboard(output='dashboard.png')
    node_death_timeline(output='death_timeline.png')
    packet_flow_snapshot(n_nodes=50, output='packet_flow.png')
    print("All visualizations generated!")