"""
Spatial Indexing Layer for CEDGM.
Stores micro-cluster IDs by spatial cell for local candidate lookup.
"""

import numpy as np
from collections import defaultdict
from itertools import product

class GridCell:
    def __init__(self, index: tuple, cell_size: float):
        self.index = index
        self.cmcs = set() # set of cmcs ids on this cell
        self.outliers = set() # set of outliers ids on this cell
        
        #  compute and store the neighbors exactly ONCE upon creation.
        self.neighbor_indices = self._compute_neighbors()
        
    def _compute_neighbors(self) -> list[tuple]:
        """
        Calculates the N-dimensional surrounding indices
        for example for 2D cell (5, 5): returns [(4,4), (4,5), (4,6), (5,4)...] #NOTE: check what do we consider neighboring cells / definition of adjacency?
        """
        #TODO
        #ranges = [(idx - 1, idx, idx + 1) for idx in self.index]
        #return list(product(*ranges))
        # handle non existing neighbors or still compute the indices anyway but be careful of none behavior
        pass
    
    @property
    def is_empty(self) -> bool:
        """Dynamically check if this cell is just dead space - no cmcs or omcs are here!"""
        return len(self.cmcs) == 0 and len(self.outliers) == 0
    
    def add_mc(self, mc_id: int, is_core: bool):
        if is_core:
            self.cmcs.add(mc_id)
        else:
            self.outliers.add(mc_id)

    def remove_mc(self, mc_id: int, is_core: bool):
        if is_core:
            self.cmcs.remove(mc_id)
        else:
            self.outliers.remove(mc_id)
    
    def get_cmcs(self):
        """ Returns the set of cmcs on this cell """
        return self.cmcs
    
    def get_outliers(self):
        """ Returns the set of outliers on this cell """
        return self.outliers
    


class GridSpace:
    def __init__(self, cell_size: float):
        """
        cell_size determines the width/height of a single grid square.
        """
        self.cell_size = cell_size
        
        self.cells: dict[tuple[int, ...], GridCell] = {} # Maps tuple index -> GridCell object

    def get_cell_index(self, point: np.ndarray) -> tuple:
        """
        TODO (Felix): Convert a multi-dimensional point into a discrete tuple index
        # take a look at how DStream handles this for multi dim
        """
        return tuple(np.floor(point / self.cell_size).astype(int))


    def get_neighboring_cells(self, cell_index: tuple) -> list[tuple]:
        """
        TODO (Felix): Return a list of the target cell AND its immediate neighbors.
        For 2D, this should return 5 or 9 cells (the center + 8 surrounding). check what the paper suggests
        NOTE: this also needs to be adaptable if data is multi-dimensional!
        """
        pass

    def get_or_create_cell(self, cell_index: tuple) -> GridCell:
        """
        If the cell doesn't exist, create it (will then also compute its neighbors)
        if it does exist, just return it.
        """
        if cell_index not in self.cells:
            self.cells[cell_index] = GridCell(cell_index, self.cell_size)
        return self.cells[cell_index]
    
    def add_mc_to_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Register a micro-cluster ID in a specific cell."""
        cell = self.get_or_create_cell(cell_index)
        cell.add_mc(mc_id, is_core)

    def remove_mc_from_cell(self, mc_id: int, cell_index: tuple, is_core: bool):
        """Remove a micro-cluster ID from a specific cell."""
        cell = self.get_or_create_cell(cell_index)
        cell.remove_mc(mc_id, is_core)

    def move_mc_between_cells(self, mc_id: int, old_cell: tuple, new_cell: tuple, is_core: bool):
        """
        Move a micro-cluster ID from one cell to another
        """
        if old_cell is not None:
            self.remove_mc_from_cell(mc_id, old_cell, is_core)
        self.add_mc_to_cell(mc_id, new_cell, is_core)

    def get_cmcs_in_cell(self, cell_index: tuple) -> set:
        return self.cells[cell_index].get_cmcs()

    def get_outliers_in_cell(self, cell_index: tuple) -> set:
        return self.cells[cell_index].get_outliers()