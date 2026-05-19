"""
Spatial Indexing Layer for CEDGM.
Maps physical coordinates to discrete grid cells.
"""

import numpy as np
from collections import defaultdict


class GridSpace:
    def __init__(self, cell_size: float):
        """
        cell_size determines the width/height of a single grid square.
        """
        self.cell_size = cell_size
        
        # Dictionary mapping a tuple (row, col) to a dictionary of CMC/OMC IDs
        # e.g., {(0, 1): {'cmcs': {1, 4}, 'outliers': {2}}}
        self.cells = defaultdict(lambda: {'cmcs': set(), 'outliers': set()})

    def get_cell_index(self, point: np.ndarray) -> tuple:
        """
        TODO (Felix): Convert a multi-dimensional point into a discrete tuple index
        # take a look at how DStream handles this for multi dim
        """
        pass

    def get_neighboring_cells(self, cell_index: tuple) -> list[tuple]:
        """
        TODO (Felix): Return a list of the target cell AND its immediate neighbors.
        For 2D, this should return 5 or 9 cells (the center + 8 surrounding). check what the paper suggests
        NOTE: this also needs to be adaptable if data is multi-dimensional!
        """
        pass
    
    def add_mc_to_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Register a micro-cluster ID in a specific cell."""
        target_set = 'cmcs' if is_core else 'outliers'
        self.cells[cell_index][target_set].add(mc_id)

    def remove_mc_from_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Remove a micro-cluster ID from a specific cell."""
        target_set = 'cmcs' if is_core else 'outliers'
        if mc_id in self.cells[cell_index][target_set]:
            self.cells[cell_index][target_set].remove(mc_id)