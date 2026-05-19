"""
micro_clusters.py
Defines the Core (CMC) and Outlier (OMC) Micro-Clusters for CEDGM.
"""

import numpy as np
import math
from enum import Enum

class MicroClusterType(Enum):
    CORE = "core"       # CEDGM's Core Micro-Cluster (CMC)
    OUTLIER = "outlier" # CEDGM's Outlier Micro-Cluster (OMC)


class MicroCluster():
    def __init__(self, mc_id: int, t_0: int, mc_type: MicroClusterType, point: np.ndarray):
        self.mc_id = mc_id # unique ID for each mircro cluster
        self.t_0 = t_0 # creation time 
        self.last_update = t_0 # # here we track the last time this MC was updated/decayed
        self.mc_type = mc_type

        self.grid_cell = None # we need to track the grid cell this cluster currently belongs to

        # CEDGM Specific Attributes: (Center, Radius, Density, Life)
        self.density = 0.0  # (Den) Physical mass/weight of the cluster
        self.life = 0.0     # (L) The energy/survival timer
        
        # keep CF tuples under the hood to calculate Center and Radius in O(1) time
        self.CF1 = np.zeros_like(point) if point is not None else 0.0
        self.CF2 = np.zeros_like(point) if point is not None else 0.0 
        
        if point is not None:
            # A new CMC starts with a life and density
            self.insert_sample(point, weight=1.0, life_boost=1.0)

    def insert_sample(self, point: np.ndarray, weight: float = 1.0, life_boost: float = 1.0):
        """
        When a point is absorbed, density increases and life is replenished.
        """
        self.density += weight
        self.life += life_boost  # replenish the survival timer or reset
        
        self.CF1 += point
        self.CF2 += np.square(point)

    def apply_decay(self, decay_factor: float, time_diff: int):
        fading_fraction = 2.0 ** (-decay_factor * time_diff)

        # decay the spatial weight/mass and the energy timer
        self.density *= fading_fraction
        self.life -= (decay_factor * time_diff) # or apply exponential fade 

        self.CF1 *= fading_fraction
        self.CF2 *= fading_fraction
        self.last_update += time_diff

    def get_center(self) -> np.ndarray:
        return self.CF1 / self.density if self.density > 0 else self.CF1
    
    def get_kernel_radius(self) -> float:
        """
        The exact mathematical variance (The inner dense core)
        """
        if self.density <= 0: return 0.0
        variance_vector = (self.CF2 / self.density) - (self.CF1 / self.density)**2
        return math.sqrt(max(0.0, np.sum(variance_vector)))

    def get_shell_radius(self, shell_multiplier: float = 1.5) -> float:
        """
        The expanded boundary used for edge detection (The "halo")
        """
        return self.get_kernel_radius() * shell_multiplier
    
    def copy(self) -> 'MicroCluster':
        new_mc = MicroCluster(self.mc_id, self.t_0, self.mc_type, point=None)
        new_mc.last_update = self.last_update
        new_mc.density = self.density
        new_mc.grid_cell = self.grid_cell
        new_mc.life = self.life
        new_mc.CF1 = self.CF1.copy() if isinstance(self.CF1, np.ndarray) else self.CF1
        new_mc.CF2 = self.CF2.copy() if isinstance(self.CF2, np.ndarray) else self.CF2
        return new_mc
