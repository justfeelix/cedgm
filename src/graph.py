"""
graph.py
Maintaining Adjacency Graph for CEDGM Macro-Clusters.
"""
from collections import defaultdict

#NOTE: feel free to change as you see fit here Paul :)
class AdjacencyGraph:
    def __init__(self, intersection_multiplier: float = 1.5):
        self.nodes = set() # set of CMC IDs -> represent the red/green points in (a) Graph Structure page 5 in the paper
        self.edges = defaultdict(set) # adjacency list: {cmc_id: set_of_connected_cmc_ids}
        # the edges dict would hold the main information for the connections
        #for example consider th: 
        # 1 <-> 2 <-> 3
        # then self.edges = {
        #     1: {2},        # CMC 1 is connected to CMC 2
        #     2: {1, 3},     # CMC 2 is the bridge, connected to 1 and 3
        #     3: {2}         # CMC 3 is connected to CMC 2
        # }
        self.intersection_multiplier = intersection_multiplier
        
        # map CMC ID -> macro clister label
        self.macro_clusters = {}

    def update_node_edges(self, target_cmc, candidate_cmcs):
        """
        TODO (Paul): 
        - calculate distance between target_cmc and all candidate_cmcs
        - if distance < (self.intersection_multiplier * target_cmc.get_radius()), add an edge
        - here remember that edges are bidirectional!
        """
        pass

    def remove_node(self, cmc_id: int):
        """
        TODO (Paul): remove the node and all its edges from the adjacency list
        """
        pass

    def recompute_connected_components(self):
        """
        TODO (Paul): 
        assign a unique ID to each connected component
        Update self.macro_clusters = {cmc_id: macro_cluster_id}
        this can be for example: 
        macro_clusters = {
            1: a, 
            2: a, 
            3: a
        }
        this way you know that CMC 1, 2 and 3 are edges for the same macro cluster
        #NOTE: keep in mind this might be called often, so we need to keep it lightweight and efficient :)
        """
        pass