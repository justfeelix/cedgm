"""
graph.py
Maintaining the Adjacency Graph for CEDGM Macro-Clusters.

Nodes are CMCs (by id). Two CMCs are connected when their centers are within
`intersection_multiplier * radius` of each other — the paper's (R1+R2)/2 rule
under fixed-radius CMCs.
Connected components ARE the live macro-clusters, exposed via self.macro_clusters and kept in sync internally after every
mutation, so callers never have to remember to trigger a recompute.

Components are maintained via localized BFS:
  - add edge bridging two components -> merge (relabel the smaller side)
  - remove edge / node -> BFS to test whether endpoints stayed connected,
    fresh label for any piece that broke off
"""
from collections import deque

from baseframework.utils import distance_calc


class AdjacencyGraph:
    def __init__(self, radius: float, intersection_multiplier: float = 1.5):
        # Adjacency list. Plain dict instead of defaultdict -> accidental reads on missing keys raise
        # KeyError instead of silently creating empty entries. An isolated CMC
        # (no overlaps yet) lives here with an empty set, so edges.keys() is
        # the authoritative node registry.
        # example:
        #   1 <-> 2 <-> 3
        # then self.edges = {1: {2}, 2: {1, 3}, 3: {2}}
        self.edges: dict[int, set[int]] = {}

        # cmc_id -> macro-cluster label. Always in sync with edges.
        # example: {1: 0, 2: 0, 3: 0} -> CMCs 1, 2, 3 form one macro-cluster.
        self.macro_clusters: dict[int, int] = {}

        self.edge_threshold = intersection_multiplier * radius

        self._next_label = 0

    def add_node(self, cmc_id: int) -> None:
        """
        Register a newly promoted CMC. It starts as its own macro-cluster
        """
        if cmc_id in self.edges:
            return
        self.edges[cmc_id] = set()
        self.macro_clusters[cmc_id] = self._fresh_label()

    def update_node_edges(self, target_cmc, candidate_cmcs) -> None:
        """
        - Diffs the target's current neighbor set against the candidates that
          actually sit within self.edge_threshold.
        - Removes broken edges first (so any resulting split is detected before
          a fresh add could mask it).
        - Adds new edges next. Each may merge two previously separate components.
        - Updates self.macro_clusters in place.
        """
        target_id = target_cmc.mc_id

        if target_id not in self.edges:
            self.add_node(target_id)

        # 1. Compute the desired neighbor set under the current geometry.
        desired: set[int] = set()
        target_center = target_cmc.center
        for c in candidate_cmcs:
            if c.mc_id == target_id:
                continue
            if c.mc_id not in self.edges:
                # candidate is an outlier or otherwise not a registered node
                continue
            if distance_calc(target_center, c.center) < self.edge_threshold:
                desired.add(c.mc_id)

        current = self.edges[target_id]
        to_remove = current - desired
        to_add = desired - current

        # 2. Apply removals first. A removal followed by an add that bridges
        # the same gap must not preempt the split detection.
        if to_remove:
            for n_id in to_remove:
                self.edges[target_id].discard(n_id)
                self.edges[n_id].discard(target_id)
            self._handle_splits(seed=target_id, severed=to_remove)

        # 3. Apply adds. Each new edge may merge two components.
        for n_id in to_add:
            self.edges[target_id].add(n_id)
            self.edges[n_id].add(target_id)
            self._merge_components(target_id, n_id)

    def remove_node(self, cmc_id: int) -> None:
        """
        Surviving neighbors may end up in different components. Splits are detected and relabeled here.
        """
        if cmc_id not in self.edges:
            return

        neighbors = list(self.edges[cmc_id])

        # Drop all incident edges (bidirectional) and the node itself.
        for n_id in neighbors:
            self.edges[n_id].discard(cmc_id)
        del self.edges[cmc_id]
        self.macro_clusters.pop(cmc_id, None)

        # With 0 or 1 surviving neighbor, no split is possible.
        if len(neighbors) >= 2:
            seed = neighbors[0]
            self._handle_splits(seed=seed, severed=set(neighbors[1:]))

    # helpers

    def _fresh_label(self) -> int:
        label = self._next_label
        self._next_label += 1
        return label

    def _bfs(self, start: int) -> set[int]:
        """I-BFS over the live adjacency list. Returns the reachable set."""
        visited = {start}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in self.edges[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        return visited

    def _handle_splits(self, seed: int, severed: set[int]) -> None:
        """
        After edges have been removed check whether any of the severed endpoints are no longer reachable.
        The component containing `seed` keeps its existing label.
        """
        if seed not in self.edges:
            return  # defensive: caller must always seed with a surviving node

        reached = self._bfs(seed)

        # Severed endpoints that ended up outside `reached` are the heads of  newly-split pieces.
        unprocessed = {n for n in severed if n in self.edges and n not in reached}

        while unprocessed:
            n = next(iter(unprocessed))
            component = self._bfs(n)
            new_label = self._fresh_label()
            for m in component:
                self.macro_clusters[m] = new_label
            unprocessed -= component

    def _merge_components(self, u: int, v: int) -> None:
        """
        If u and v sit in different components, relabel the smaller side to match the larger side's
        label, so downstream consumers see minimal label churn.
        """
        label_u = self.macro_clusters[u]
        label_v = self.macro_clusters[v]
        if label_u == label_v:
            return

        # One pass over the label map to collect both sides.
        nodes_u, nodes_v = [], []
        for cmc_id, lbl in self.macro_clusters.items():
            if lbl == label_u:
                nodes_u.append(cmc_id)
            elif lbl == label_v:
                nodes_v.append(cmc_id)

        if len(nodes_u) >= len(nodes_v):
            survivor_label, losers = label_u, nodes_v
        else:
            survivor_label, losers = label_v, nodes_u

        for m in losers:
            self.macro_clusters[m] = survivor_label
