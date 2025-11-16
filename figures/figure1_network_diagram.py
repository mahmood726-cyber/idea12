"""
Figure 1: Network Diagram for Coronary Stents Meta-Analysis
Publication-quality network diagram showing study connections
"""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

def create_network_diagram(output_path='figure1_network_diagram', dpi=300):
    """
    Create network diagram for coronary stents example

    Network: 24 studies, 4 treatments (BMS, DES, BAS, CS)
    Direct comparisons: 5 of 6 possible
    """

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Define network structure
    treatments = ['BMS', 'DES', 'BAS', 'CS']

    # Number of studies per comparison (from cardiovascular example)
    comparisons = {
        ('BMS', 'DES'): 14,  # Most evidence
        ('BMS', 'CS'): 4,
        ('DES', 'BAS'): 3,
        ('DES', 'CS'): 2,
        ('BAS', 'CS'): 1,
        # No direct BMS vs BAS comparison (indirect only)
    }

    # Total patients per treatment (synthetic)
    n_patients = {
        'BMS': 9842,
        'DES': 12456,
        'BAS': 2634,
        'CS': 3524
    }

    # Create graph
    G = nx.Graph()
    G.add_nodes_from(treatments)

    for (t1, t2), n_studies in comparisons.items():
        G.add_edge(t1, t2, weight=n_studies)

    # Layout - circular for clarity
    pos = nx.circular_layout(G)

    # Adjust positions for better spacing
    scale = 2.0
    pos = {k: (v[0]*scale, v[1]*scale) for k, v in pos.items()}

    # Draw edges with width proportional to number of studies
    edge_widths = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]

    nx.draw_networkx_edges(
        G, pos,
        width=edge_widths,
        alpha=0.6,
        edge_color='gray',
        ax=ax
    )

    # Add edge labels (number of studies)
    edge_labels = {(u, v): f"{G[u][v]['weight']}" for u, v in G.edges()}
    nx.draw_networkx_edge_labels(
        G, pos,
        edge_labels,
        font_size=10,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
        ax=ax
    )

    # Draw nodes with size proportional to number of patients
    node_sizes = [n_patients[node] * 0.5 for node in G.nodes()]

    nx.draw_networkx_nodes(
        G, pos,
        node_size=node_sizes,
        node_color='lightblue',
        edgecolors='black',
        linewidths=2,
        ax=ax
    )

    # Draw node labels
    nx.draw_networkx_labels(
        G, pos,
        font_size=12,
        font_weight='bold',
        ax=ax
    )

    # Add treatment full names as annotations
    treatment_names = {
        'BMS': 'Bare Metal Stent',
        'DES': 'Drug-Eluting Stent',
        'BAS': 'Bioabsorbable Stent',
        'CS': 'Covered Stent'
    }

    offset_y = -0.4
    for node, (x, y) in pos.items():
        ax.text(x, y + offset_y, treatment_names[node],
               ha='center', va='top', fontsize=9, style='italic')

    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], color='gray', linewidth=7, label='14 studies (BMS-DES)'),
        plt.Line2D([0], [0], color='gray', linewidth=2, label='4 studies (BMS-CS)'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue',
                  markersize=15, label=f'Node size ∝ Total N\n(range: 2,634-12,456)')
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9)

    # Add title and caption
    ax.set_title('Network Meta-Analysis: Coronary Stents for Acute Coronary Syndrome\n' +
                '24 Studies, 28,456 Patients, 4 Treatments',
                fontsize=14, fontweight='bold', pad=20)

    # Add caption
    caption = ('Edge width proportional to number of direct comparison studies.\n' +
              'Node size proportional to total patients randomized to treatment.\n' +
              'No direct comparison between BMS and BAS (indirect evidence only).')

    fig.text(0.5, 0.02, caption, ha='center', fontsize=9, style='italic',
            wrap=True)

    # Clean up axes
    ax.axis('off')
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3.5)

    # Adjust layout
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])

    # Save in multiple formats
    plt.savefig(f'{output_path}.png', dpi=dpi, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    plt.savefig(f'{output_path}.eps', format='eps', bbox_inches='tight')

    print(f"✓ Figure 1 saved: {output_path}.{{png,pdf,eps}}")
    print(f"  Resolution: {dpi} dpi")
    print(f"  Format: Publication-ready for RSM")

    return fig

if __name__ == '__main__':
    fig = create_network_diagram()
    plt.show()
