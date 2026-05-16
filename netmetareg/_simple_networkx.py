"""
Lightweight subset of the networkx API used by netmetareg.

This keeps core network functionality available in minimal environments
where the optional third-party dependency is not installed.
"""

from __future__ import annotations

from collections import deque
from itertools import combinations
import math


class NetworkXNoPath(Exception):
    """Raised when no path exists between two nodes."""


class Graph:
    """Undirected graph with a small networkx-compatible surface."""

    def __init__(self):
        self._adj = {}

    def add_node(self, node):
        self._adj.setdefault(node, {})

    def add_edge(self, u, v, **attrs):
        self.add_node(u)
        self.add_node(v)
        if v not in self._adj[u]:
            data = dict(attrs)
            self._adj[u][v] = data
            self._adj[v][u] = data
        else:
            self._adj[u][v].update(attrs)
            self._adj[v][u] = self._adj[u][v]

    def has_edge(self, u, v):
        return u in self._adj and v in self._adj[u]

    def remove_edge(self, u, v):
        if self.has_edge(u, v):
            del self._adj[u][v]
            del self._adj[v][u]

    def copy(self):
        other = Graph()
        for node in self.nodes():
            other.add_node(node)
        for u, v in self.edges():
            other.add_edge(u, v, **self._adj[u][v].copy())
        return other

    def to_directed(self):
        graph = DiGraph()
        for node in self.nodes():
            graph.add_node(node)
        for u, v in self.edges():
            attrs = self._adj[u][v].copy()
            graph.add_edge(u, v, **attrs)
            graph.add_edge(v, u, **attrs)
        return graph

    def nodes(self):
        return list(self._adj)

    def edges(self):
        seen = set()
        edges = []
        for u, neighbors in self._adj.items():
            for v in neighbors:
                key = frozenset((u, v))
                if key in seen:
                    continue
                seen.add(key)
                edges.append((u, v))
        return edges

    def degree(self):
        return [(node, len(neighbors)) for node, neighbors in self._adj.items()]

    def number_of_nodes(self):
        return len(self._adj)

    def number_of_edges(self):
        return len(self.edges())

    def __getitem__(self, node):
        return self._adj[node]


class DiGraph:
    """Directed graph used only for simple cycle enumeration."""

    def __init__(self):
        self._adj = {}

    def add_node(self, node):
        self._adj.setdefault(node, {})

    def add_edge(self, u, v, **attrs):
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = dict(attrs)

    def nodes(self):
        return list(self._adj)

    def edges(self):
        return [(u, v) for u, neighbors in self._adj.items() for v in neighbors]

    def __getitem__(self, node):
        return self._adj[node]


def connected_components(graph):
    remaining = set(graph.nodes())
    components = []

    while remaining:
        start = remaining.pop()
        queue = deque([start])
        component = {start}

        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if neighbor in component:
                    continue
                component.add(neighbor)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                queue.append(neighbor)

        components.append(component)

    return components


def is_connected(graph):
    if graph.number_of_nodes() <= 1:
        return True
    return len(connected_components(graph)) == 1


def has_path(graph, source, target):
    if source == target:
        return True

    seen = {source}
    queue = deque([source])

    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor == target:
                return True
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)

    return False


def all_simple_paths(graph, source, target, cutoff=None):
    if source not in graph.nodes() or target not in graph.nodes():
        raise NetworkXNoPath(f"No path between {source} and {target}")

    max_depth = float("inf") if cutoff is None else cutoff
    paths = []

    def dfs(node, path):
        if len(path) - 1 > max_depth:
            return
        if node == target:
            paths.append(path[:])
            return
        for neighbor in graph[node]:
            if neighbor in path:
                continue
            path.append(neighbor)
            dfs(neighbor, path)
            path.pop()

    dfs(source, [source])
    return paths


def simple_cycles(graph):
    cycles = set()
    nodes = graph.nodes()

    def normalize(path):
        cycle = path[:]
        rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
        return min(rotations)

    def dfs(start, node, path):
        for neighbor in graph[node]:
            if neighbor == start and len(path) >= 3:
                cycles.add(normalize(path[:]))
                continue
            if neighbor in path or len(path) >= len(nodes):
                continue
            path.append(neighbor)
            dfs(start, neighbor, path)
            path.pop()

    for start in nodes:
        dfs(start, start, [start])

    return [list(cycle) for cycle in cycles]


def enumerate_all_cliques(graph):
    nodes = sorted(graph.nodes(), key=str)
    for size in range(1, len(nodes) + 1):
        for combo in combinations(nodes, size):
            if all(graph.has_edge(u, v) for u, v in combinations(combo, 2)):
                yield list(combo)


def average_clustering(graph):
    scores = []
    for node in graph.nodes():
        neighbors = list(graph[node])
        degree = len(neighbors)
        if degree < 2:
            scores.append(0.0)
            continue
        possible = degree * (degree - 1) / 2
        triangles = sum(
            1 for u, v in combinations(neighbors, 2) if graph.has_edge(u, v)
        )
        scores.append(triangles / possible)
    return sum(scores) / len(scores) if scores else 0.0


def average_shortest_path_length(graph):
    nodes = graph.nodes()
    if len(nodes) <= 1:
        return 0.0

    total = 0
    count = 0

    for i, source in enumerate(nodes):
        distances = _shortest_path_lengths(graph, source)
        for target in nodes[i + 1:]:
            total += distances[target]
            count += 1

    return total / count if count else 0.0


def spring_layout(graph, k=2, iterations=50):
    del k, iterations
    nodes = sorted(graph.nodes(), key=str)
    n_nodes = len(nodes)
    if n_nodes == 0:
        return {}

    positions = {}
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i) / n_nodes
        positions[node] = (math.cos(angle), math.sin(angle))
    return positions


def draw_networkx_nodes(graph, pos, node_color="lightblue", node_size=3000, ax=None):
    ax = _get_ax(ax)
    xs = [pos[node][0] for node in graph.nodes()]
    ys = [pos[node][1] for node in graph.nodes()]
    ax.scatter(xs, ys, s=node_size, c=node_color, edgecolors="black", zorder=3)


def draw_networkx_edges(graph, pos, width=1, alpha=0.6, ax=None):
    ax = _get_ax(ax)
    widths = width if isinstance(width, list) else [width] * len(graph.edges())
    for (u, v), edge_width in zip(graph.edges(), widths):
        ax.plot(
            [pos[u][0], pos[v][0]],
            [pos[u][1], pos[v][1]],
            linewidth=edge_width,
            alpha=alpha,
            color="gray",
            zorder=1,
        )


def draw_networkx_labels(graph, pos, font_size=10, font_weight="bold", ax=None):
    ax = _get_ax(ax)
    for node, (x, y) in pos.items():
        ax.text(x, y, str(node), ha="center", va="center", fontsize=font_size, fontweight=font_weight, zorder=4)


def draw_networkx_edge_labels(graph, pos, edge_labels, font_size=8, ax=None):
    ax = _get_ax(ax)
    for (u, v), label in edge_labels.items():
        x = (pos[u][0] + pos[v][0]) / 2
        y = (pos[u][1] + pos[v][1]) / 2
        ax.text(x, y, str(label), fontsize=font_size, ha="center", va="center", zorder=5)


def _shortest_path_lengths(graph, source):
    distances = {source: 0}
    queue = deque([source])

    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor in distances:
                continue
            distances[neighbor] = distances[node] + 1
            queue.append(neighbor)

    return distances


def _get_ax(ax):
    if ax is not None:
        return ax
    import matplotlib.pyplot as plt

    return plt.gca()
