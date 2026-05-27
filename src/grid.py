"""
Spatial Indexing Layer for CEDGM.
Stores micro-cluster IDs by spatial cell for local candidate lookup.
"""

import numpy as np
from collections import defaultdict
from itertools import product


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
        Convert a multi-dimensional point into a discrete tuple index
        """
        return tuple(np.floor(point / self.cell_size).astype(int))


    def get_neighboring_cells(self, cell_index: tuple) -> list[tuple]:
        """
        Returns a list of the target cell AND its immediate neighbors.
        Adapts dynamically to the dimensionality of the cell_index tuple (e.g., returns 9 cells for 2D, 27 cells for 3D).
        """

        # For every dimension in the tuple, get (idx-1, idx, idx+1)
        ranges = [(idx - 1, idx, idx + 1) for idx in cell_index]
        
        # Compute the Cartesian product of all dimensional ranges
        return list(product(*ranges))
    
    def add_mc_to_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Register a micro-cluster ID in a specific cell."""
        target_set = 'cmcs' if is_core else 'outliers'
        self.cells[cell_index][target_set].add(mc_id)

    def remove_mc_from_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Remove a micro-cluster ID from a specific cell."""
        target_set = 'cmcs' if is_core else 'outliers'
        if mc_id in self.cells[cell_index][target_set]:
            self.cells[cell_index][target_set].remove(mc_id)

    def move_mc_between_cells(self, mc_id: int, old_cell: tuple, new_cell: tuple, is_core: bool):
        """
        Move a micro-cluster ID from one cell to another
        """
        if old_cell is not None:
            self.remove_mc_from_cell(mc_id, old_cell, is_core)
        self.add_mc_to_cell(mc_id, new_cell, is_core)

    def get_cmcs_in_cell(self, cell_index: tuple) -> set:
        return set(self.cells[cell_index]['cmcs'])

    def get_outliers_in_cell(self, cell_index: tuple) -> set:
        return set(self.cells[cell_index]['outliers'])