"""
cedgm.py
Main Orchestrator for CEDGM (Pure Online Approach)
"""
import math
from typing import override

import numpy as np
from baseframework.stream_clustering import OnlinePhase_StreamClusterer
from baseframework.utils import distance_calc

from .micro_clusters import MicroCluster, MicroClusterType
from .grid import GridSpace
from .graph import AdjacencyGraph


class CEDGM(OnlinePhase_StreamClusterer):
    def __init__(self, radius: float, min_threshold: float, decay: int,
                 grid_granularity: int = 30, cell_size: float = 0.5, Tp: int | None = None):
        super().__init__()

        if decay <= 0:
            raise ValueError(f"decay must be positive, got {decay}")
        if radius <= 0:
            raise ValueError(f"radius must be positive, got {radius}")
        if min_threshold <= 0:
            raise ValueError(f"min_threshold must be positive, got {min_threshold}")
        if cell_size <= 0:
            raise ValueError(f"cell_size must be positive, got {cell_size}")

        self.radius = radius
        self.min_threshold = min_threshold
        self.decay = decay

        # Paper Eq. 2: FD = 1/DC
        self.fade_factor = 1.0 / decay

        # Tp: Tp-choice is not specified in the paper; we follow the DenStream heuristic.
        # Formula: Tp = ceil((1/λ) * log(βμ / (βμ - 1))), with β=0.2 (DenStream default).
        beta = 0.2
        bm = beta * min_threshold
        if bm > 1:
            Tp_auto = math.ceil((1.0 / self.fade_factor) * math.log(bm / (bm - 1)))
        else:
            Tp_auto = max(1, decay // 10)
        self.Tp = Tp if Tp is not None else max(1, Tp_auto)

        self.last_cleanup_t = 0

        # NOTE: the paper proposes to calculate the resolution (grid size), this requires knowing Vmin and Vmax values of the dataset which is not really realistic in a stream!
        #so instead we can just pass the cell size as a hyperparamter
        self.grid = GridSpace(cell_size)

        #NOTE: the intersection multiplier is 1.5 in the paper, we can also make this a hyperparamtere as well when testing
        # The graph caches `intersection_multiplier * radius` once as its edge threshold,
        # so it needs both values up front.
        self.graph = AdjacencyGraph(radius=radius, intersection_multiplier=1.5)

        # Memory
        self.cmcs = {}      # mc_id -> MicroCluster (CORE)
        self.outliers = {}  # mc_id -> MicroCluster (OUTLIER)
        self.mc_counter = 0

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _handle_mc_cell_move(self, mc: MicroCluster, is_core: bool):
        """Update the grid if the MC center has drifted into a new cell."""
        new_cell = self.grid.get_cell_index(mc.center)
        if new_cell != mc.grid_cell:
            assert mc.grid_cell is not None
            self.grid.move_mc_between_cells(mc.mc_id, mc.grid_cell, new_cell, is_core)
            mc.grid_cell = new_cell

    def _collect_cmc_candidates_around(self, affected_cmc: MicroCluster) -> list:
        """Return all CMCs in the neighboring cells of affected_cmc (excluding itself)."""
        cell_idx = affected_cmc.grid_cell
        assert cell_idx is not None
        neighboring_cells = self.grid.get_neighboring_cells(cell_idx)

        if neighboring_cells is None:
            neighboring_cells = [cell_idx]

        candidates = []
        for neighbor_cell in neighboring_cells:
            for cmc_id in self.grid.get_cmcs_in_cell(neighbor_cell):
                if cmc_id != affected_cmc.mc_id and cmc_id in self.cmcs:
                    candidates.append(self.cmcs[cmc_id])
        return candidates

    def _promote_omc_to_cmc(self, omc: MicroCluster):
        """Move an OMC to the CMC set, update grid and graph."""
        omc_id = omc.mc_id

        # Grid: outlier slot -> cmc slot
        assert omc.grid_cell is not None
        self.grid.remove_mc_from_cell(omc_id, omc.grid_cell, is_core=False)
        self.grid.add_mc_to_cell(omc_id, omc.grid_cell, is_core=True)

        # Dictionaries
        del self.outliers[omc_id]
        self.cmcs[omc_id] = omc

        # Graph: register node (update_node_edges is defensive, but add_node here
        # ensures the node exists before we collect candidates)
        if omc_id not in self.graph.edges:
            self.graph.add_node(omc_id)

    # ------------------------------------------------------------------
    # Core online method
    # ------------------------------------------------------------------

    @override
    def learn_one(self, x: np.ndarray, t: int) -> tuple:
        """Process a single incoming point (Paper Fig. 3, Step 1).

        life_boost and initial life are hard-coded to 1.0. With aggressive decay
        (small decay value) MCs may die early. Future: expose life_boost as a
        hyperparameter or couple it to decay.
        """
        # GRAPH RESPONSIBILITY:
        # The orchestrator owns the job of notifying the graph whenever the CMC
        # population changes. The graph cannot detect drift on its own. Concretely:
        #   - new CMC promoted from an outlier  -> self.graph.add_node(cmc_id)
        #                                          then self.graph.update_node_edges(cmc, candidates)
        #   - existing CMC absorbed a point (center may have moved)
        #                                       -> self.graph.update_node_edges(cmc, candidates)
        #   - CMC died via decay                -> self.graph.remove_node(cmc_id)
        # The graph keeps self.graph.macro_clusters in sync internally, so there
        # is no separate "recompute" call to make.
        event_log = []
        affected_cmc = None
        summary_id = None

        # 1. Spatial lookup
        cell_idx = self.grid.get_cell_index(x)
        neighboring_cells = self.grid.get_neighboring_cells(cell_idx)

        if neighboring_cells is None:
            event_log.append("WARNING: get_neighboring_cells returned None, using current cell only")
            neighboring_cells = [cell_idx]

        candidate_cmc_ids = set()
        candidate_omc_ids = set()
        for neighbor_cell in neighboring_cells:
            candidate_cmc_ids.update(self.grid.get_cmcs_in_cell(neighbor_cell))
            candidate_omc_ids.update(self.grid.get_outliers_in_cell(neighbor_cell))

        # 2. Find nearest CMC and OMC
        nearest_cmc, dist_cmc = None, float('inf')
        for cmc_id in candidate_cmc_ids:
            cmc = self.cmcs[cmc_id]
            d = distance_calc(x, cmc.center)
            if d < dist_cmc:
                dist_cmc = d
                nearest_cmc = cmc

        nearest_omc, dist_omc = None, float('inf')
        for omc_id in candidate_omc_ids:
            omc = self.outliers[omc_id]
            d = distance_calc(x, omc.center)
            if d < dist_omc:
                dist_omc = d
                nearest_omc = omc

        # 3. Decision tree (Paper Step 1, Fig. 3) — nearest MC within radius wins
        if dist_cmc <= dist_omc and dist_cmc <= self.radius:
            # Fall 1: absorb into existing CMC
            assert nearest_cmc is not None
            nearest_cmc.insert_sample(x, weight=1.0, life_boost=1.0)
            self._handle_mc_cell_move(nearest_cmc, is_core=True)
            affected_cmc = nearest_cmc
            summary_id = nearest_cmc.mc_id
            event_log.append(f"CMC {nearest_cmc.mc_id}: absorbed sample")

        elif dist_omc <= self.radius:
            # Fall 2: absorb into existing OMC, check promotion
            assert nearest_omc is not None
            nearest_omc.insert_sample(x, weight=1.0, life_boost=1.0)
            self._handle_mc_cell_move(nearest_omc, is_core=False)

            if nearest_omc.is_promotable(self.min_threshold):
                nearest_omc.promote_to_core()
                self._promote_omc_to_cmc(nearest_omc)
                affected_cmc = nearest_omc
                event_log.append(f"OMC {nearest_omc.mc_id}: PROMOTED to CMC")

            summary_id = nearest_omc.mc_id

        else:
            # Fall 3: create new OMC
            new_omc = MicroCluster(self.mc_counter, t, MicroClusterType.OUTLIER, x)
            self.mc_counter += 1
            new_omc.grid_cell = cell_idx
            self.outliers[new_omc.mc_id] = new_omc
            self.grid.add_mc_to_cell(new_omc.mc_id, cell_idx, is_core=False)
            summary_id = new_omc.mc_id
            event_log.append(f"New OMC created: {new_omc.mc_id}")

        # 4. Graph update (only when a CMC was touched or promoted)
        # add_node already ran in _promote_omc_to_cmc for new promotions;
        # for pure absorption the node is already registered.
        if affected_cmc is not None:
            candidates = self._collect_cmc_candidates_around(affected_cmc)
            self.graph.update_node_edges(affected_cmc, candidates)
            event_log.append(f"Graph updated for CMC {affected_cmc.mc_id}")

        # 5. Periodic pruning
        if t - self.last_cleanup_t >= self.Tp:
            self._periodic_cleanup(t, event_log)
            self.last_cleanup_t = t

        # 6. Return
        cluster_id = self.graph.macro_clusters.get(summary_id, -1) if summary_id is not None else -1
        return (summary_id, cluster_id, " | ".join(event_log) if event_log else "no events")

    # ------------------------------------------------------------------
    # Pruning (Paper Step 2: Kill Weak CMCs)
    # ------------------------------------------------------------------

    def _periodic_cleanup(self, t: int, event_log: list):
        """Apply decay to all MCs, then prune dead ones."""

        # Phase 1: decay
        for mc in list(self.cmcs.values()) + list(self.outliers.values()):
            time_diff = t - mc.last_update
            mc.apply_decay(self.fade_factor, time_diff)

        # Phase 2: prune dead CMCs (Grid -> Graph -> Dict)
        # Killing on density < min_threshold extends the paper (which only specifies life <= 0).
        # Inspired by DenStream: removes degenerate CMCs that faded below the promotion threshold.
        dead_cmc_ids = [
            mc_id for mc_id, mc in self.cmcs.items()
            if mc.life <= 0 or mc.density < self.min_threshold
        ]
        for mc_id in dead_cmc_ids:
            mc = self.cmcs[mc_id]
            self.grid.remove_mc_from_cell(mc_id, mc.grid_cell, is_core=True)
            self.graph.remove_node(mc_id)
            del self.cmcs[mc_id]
            event_log.append(f"CMC {mc_id} pruned (life={mc.life:.3f})")

        # Phase 3: prune dead OMCs (Grid -> Dict, no graph touch)
        dead_omc_ids = [
            mc_id for mc_id, mc in self.outliers.items()
            if mc.life <= 0
        ]
        for mc_id in dead_omc_ids:
            mc = self.outliers[mc_id]
            self.grid.remove_mc_from_cell(mc_id, mc.grid_cell, is_core=False)
            del self.outliers[mc_id]
            event_log.append(f"OMC {mc_id} pruned (life={mc.life:.3f})")

        event_log.append(
            f"Cleanup t={t}: {len(dead_cmc_ids)} CMCs, {len(dead_omc_ids)} OMCs removed"
        )

    # ------------------------------------------------------------------

    def predict(self, assignments=None) -> dict:
        """Return live macro-cluster labels. Returns a copy to protect
        internal state from external mutation."""
        return dict(self.graph.macro_clusters)
