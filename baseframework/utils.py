import numpy as np

_distance_calls = 0

def reset_distance_calls():
    """Set the global distance-call counter back to zero."""
    global _distance_calls
    _distance_calls = 0

def get_distance_calls():
    """Return the cumulative number of distance_calc invocations since the last reset."""
    return _distance_calls

def distance_calc(pos1, pos2, dist="euclidean", dim_weight=None):
    global _distance_calls
    _distance_calls += 1
    if dim_weight is None:
        dim_weight = np.ones(pos1.shape[-1])
    if dist == "euclidean":
        if len(pos1.shape) == 1 or len(pos2.shape) == 1:
            return np.sqrt(np.sum(dim_weight * np.square(pos1 - pos2), axis=-1))
        else:
            return np.sqrt(np.sum(dim_weight * np.square(pos1[:, None, :] - pos2[None, :, :]), axis=-1))
    else:
        raise NotImplementedError
