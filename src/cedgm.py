"""
cedgm.py
Main Orchestrator for CEDGM (Pure Online Approach)
"""
import numpy as np
from baseframework.stream_clustering import OnlinePhase_StreamClusterer

from .micro_clusters import MicroCluster, MicroClusterType
from .grid import GridSpace
from .graph import AdjacencyGraph

#NOTE: change as you see fit :)
class CEDGM(OnlinePhase_StreamClusterer):
    def __init__(self, radius: float, min_threshold: float, decay: int, grid_granularity: int = 30, cell_size: float = 0.5):
        super().__init__()

        # CEDGM Parameters (di from the paper)
        # #TODO: (Anton) 
        # radius: Minimum allowable distance to CMC 
        # min threshold: Minimum density to form a CMC
        # decay: how many past samples matter
        # from decay calculate the fade (Equation 2)

        # NOTE: the paper proposes to calculate the resolution (grid size), this requires knowing Vmin and Vmax values of the dataset which is not really realistic in a stream! 
        #so instead we can just pass the cell size as a hyperparamter
        self.grid = GridSpace(cell_size)

        #NOTE: the intersection multiplier is 1.5 in the paper, we can also make this a hyperparamtere as well when testing
        self.graph = AdjacencyGraph(intersection_multiplier=1.5)

        # Memory
        self.cmcs = {} # CMC_ID -> MicroCluster
        self.outliers = {} # OMC_ID -> MicroCluster
        self.mc_counter = 0


    def learn_one(self, x: np.ndarray, t: int) -> tuple:
        """
        Process a single incoming point
        """
        event_log = []

        # conceptual workflow should be: 
        # 1. find grid index 
        # 2. update/create micro-cluster 
        # 3. update graph for affected CMCs only
        # 4.  prune/decay 
        # 5. recompute macro-clusters
        
        # 1. Spatial Mapping
        cell_idx = self.grid.get_cell_index(x)
        neighboring_cells_ids = self.grid.get_neighboring_cells(cell_idx)
        
        # fetch candidates
        candidate_cmc_ids = set()
        candidate_omc_ids = set()
        for cell_idx in neighboring_cells_ids:
            candidate_cmc_ids.update(self.grid.get_cmcs_in_cell(cell_index=cell_idx))
            candidate_omc_ids.update(self.grid.get_outliers_in_cell(cell_index=cell_idx))

        # TODO (Anton): merging & absorption
        # NOTE: this is same as denstream but remember updating and the grid and always consider if it changes the graph structure!

        # - find nearest CMC among candidate_cmc_ids. If fits (radius check) -> insert & update grid
        # - if fails, find nearest OMC -> If fits, insert
        # - if OMC weight >= threshold -> promote to CMC
        # - If fits nowhere, create new OMC
        
        # TODO: Graph Update
        # - if a CMC was updated or newly promoted, call self.graph.update_node_edges()
        # - call self.graph.recompute_connected_components()

        # TODO: prunning 
        Tp = None 
        if (Tp): #calculate Tp and prune every Tp steps
            self._periodic_cleanup(t, event_log)

        return (0, 0, " | ".join(event_log)) # Baseframework return signature
    

        
    def _periodic_cleanup(self, t: int, event_log: list):
        """
        TODO (Anton): 
        - apply decay to all CMCs and Outliers.
        - consider graph changes when removing/deleting an mc
        """
        pass

    def predict(self, assignments=None) -> list:
        """
        CEDGM is pure online! no offline here
        we just return the live graph state
        """
        # Return a dictionary of {cmc_id: macro_cluster_label} directly
        # NOTE: it would be cool if later we can add visualization of the graph structure and how it changes over time :)
        return self.graph.macro_clusters