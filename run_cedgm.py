"""
Main entry point for running and experimenting with CEDGM.
Besides the CLI, this module exposes `evaluate_params` — a pure function that
runs the full stream for one parameter configuration and returns a single
comparable score (CMM minus a cluster-count penalty) plus diagnostics. That is
the unit a programmatic hyperparameter search calls repeatedly.
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'baseframework/')

import argparse
import numpy as np
from src.cedgm import CEDGM
from baseframework.datahandler import load_data
try:
    from baseframework.metrics.cmm import get_cmm
    _METRICS_OK = True
except ImportError:
    print("Warning: Could not import metrics!")
    _METRICS_OK = False

def iter_batches(X, batch_size, points_per_timestep):
    """Yield (batch_index, batch, timestamps) covering all of X.
    Logical timestamps advance one tick per `points_per_timestep` points, matching
    the original loop; the final (possibly short) remainder batch is included.
    """
    n = len(X)
    num_batches = n // batch_size
    for i in range(num_batches + 1):
        start = i * batch_size
        end = min((i + 1) * batch_size, n)
        if start >= end:
            break
        batch = X[start:end]
        timestamps = np.arange(start, end) // points_per_timestep
        yield i, batch, timestamps


def run_stream(X, *, radius, min_threshold, decay, cell_size,
               batch_size=500, points_per_timestep=1, on_batch=None):
    """Run the full online stream for one configuration.
    Returns (assignments, mapping) where assignments[i] is the summary_id (CMC or
    OMC) the i-th point was absorbed into, and mapping is the final
    summary_id -> macro-cluster label dict from `predict()`.
    `on_batch(i, batch, timestamps, cedgm, assignments)` is called after each
    batch for live logging; pass None to stay silent.
    """
    cedgm = CEDGM(radius=radius, min_threshold=min_threshold,
                  decay=decay, cell_size=cell_size)

    assignments = []
    for i, batch, timestamps in iter_batches(X, batch_size, points_per_timestep):
        results = cedgm.learn(batch, timestamps)
        # summary_id (r[0]) is the CMC/OMC the point was absorbed into
        assignments.extend(r[0] for r in results)
        if on_batch is not None:
            on_batch(i, batch, timestamps, cedgm, assignments)

    mapping = cedgm.predict()
    return assignments, mapping

def score_clustering(X, y, labels, *, count_penalty_weight=0.5, cmm_k=5):
    """Score a clustering with CMM minus a cluster-count penalty.
    score = CMM - count_penalty_weight * |n_clusters - true_k| / true_k
    CMM (<= 1.0, higher is better) measures clustering quality against the
    ground truth; the penalty pulls the number of discovered clusters toward the
    true class count, directly discouraging over-segmentation. Degenerate
    clusterings (< 2 non-noise clusters) get a sentinel score of -inf so a search
    never selects them.
    Returns a dict with the raw `cmm`, diagnostics, and the combined `score`.
    """
    labels = np.asarray(labels)
    y = np.asarray(y)

    n_clusters = int(len(np.unique(labels[labels != -1])))
    noise_frac = float(np.mean(labels == -1))
    true_k = int(len(np.unique(y[y != -1])))

    result = {
        "cmm": float("nan"),
        "score": float("-inf"),
        "n_clusters": n_clusters,
        "true_k": true_k,
        "noise_frac": noise_frac,
        "count_penalty": float("nan"),
        "valid": False,
        "reason": "",
    }

    if not _METRICS_OK:
        result["reason"] = "metrics unavailable"
        return result
    if n_clusters < 2:
        result["reason"] = f"degenerate: {n_clusters} non-noise cluster(s)"
        return result

    w = np.ones(len(X))
    cmm = float(get_cmm(np.asarray(X), y, labels, w, k=cmm_k))
    count_penalty = count_penalty_weight * abs(n_clusters - true_k) / max(true_k, 1)

    result.update(
        cmm=cmm,
        count_penalty=float(count_penalty),
        score=float(cmm - count_penalty),
        valid=True,
        reason="ok",
    )
    return result


def evaluate_params(X, y, *, radius, min_threshold, decay, cell_size,
                    batch_size=500, points_per_timestep=1,
                    count_penalty_weight=0.5, cmm_k=5):
    """Run CEDGM once for one configuration and return its score dict.
    This is the building block for hyperparameter search: parameters in, one
    comparable `score` (plus diagnostics and the originating `params`) out. The
    run is deterministic, so a single call per configuration is sufficient.
    """
    assignments, mapping = run_stream(
        X, radius=radius, min_threshold=min_threshold, decay=decay,
        cell_size=cell_size, batch_size=batch_size,
        points_per_timestep=points_per_timestep,
    )
    labels = np.array([mapping.get(a, -1) for a in assignments])

    result = score_clustering(X, y, labels,
                              count_penalty_weight=count_penalty_weight,
                              cmm_k=cmm_k)
    result["params"] = {
        "radius": radius,
        "min_threshold": min_threshold,
        "decay": decay,
        "cell_size": cell_size,
    }
    return result

def main():
    parser = argparse.ArgumentParser(description="Run CEDGM Clustering Simulation")

    # dataset / batching
    parser.add_argument('--dataset', type=str, default='complex9',
                        help='Dataset name: complex9, rbf3, har, stream_densired, spiral')
    parser.add_argument('--batch_size', type=int, default=500,
                        help='Number of instances per batch')

    # logical Time parameter
    parser.add_argument('--points_per_timestep', type=int, default=1,
                        help='How many data points arrive within a single logical time step (t)')

    # CEDGM parameters
    parser.add_argument('--radius', type=float, default=0.05,
                        help='Minimum allowable distance to CMC center (Radius)')
    parser.add_argument('--min_threshold', type=float, default=5.0,
                        help='Minimum density required to form a CMC (Thdensity)')
    parser.add_argument('--decay', type=int, default=100,
                        help='Decay parameter: how many past samples matter (DC)')
    parser.add_argument('--cell_size', type=float, default=0.1,
                        help='Physical width of a grid cell (Resolution)')

    # evaluation
    parser.add_argument('--eval_interval', type=int, default=1,
                        help='Print live macro-cluster count every N batches (0 = never)')
    parser.add_argument('--count_penalty_weight', type=float, default=0.5,
                        help='Weight of the |n_clusters - true_k| penalty in the score')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress per-batch progress logging')

    args = parser.parse_args()

    print(f"Loading data '{args.dataset}'...")
    X, y = load_data(args.dataset)

    num_batches = len(X) // args.batch_size

    print(f"\n=======================================================")
    print(f"STARTING CEDGM STREAM PROCESSING: {num_batches} batches of size {args.batch_size}")
    print(f"PARAMETERS: radius={args.radius}  min_threshold={args.min_threshold}  "
          f"decay={args.decay}  cell_size={args.cell_size}")
    print(f"=======================================================\n")

    def on_batch(i, batch, timestamps, cedgm, assignments):
        batch_assignments = assignments[-len(batch):]
        print(f"   Batch {i:>4d} | points so far: {len(assignments):>6d} | "
              f"Current Time (t): {timestamps[-1]}")

        if args.eval_interval > 0 and (i + 1) % args.eval_interval == 0:
            cluster_dict = cedgm.predict()
            labels = np.array([cluster_dict.get(a, -1) for a in batch_assignments])
            num_clusters = len(np.unique(labels[labels != -1]))
            print(f"          [Live Graph] Active Macro-Clusters tracking: {num_clusters}")

    assignments, mapping = run_stream(
        X, radius=args.radius, min_threshold=args.min_threshold,
        decay=args.decay, cell_size=args.cell_size,
        batch_size=args.batch_size, points_per_timestep=args.points_per_timestep,
        on_batch=None if args.quiet else on_batch,
    )

    labels = np.array([mapping.get(a, -1) for a in assignments])
    result = score_clustering(X, y, labels,
                              count_penalty_weight=args.count_penalty_weight)

    print(f"\n--- Stream Finished ---")
    print(f"    Total points: {len(assignments)}")
    print(f"\n=== Final Evaluation (full stream) ===")
    if not result["valid"]:
        print(f"    INVALID: {result['reason']}")
        print(f"    clusters found: {result['n_clusters']}  (true k = {result['true_k']})")
        print(f"    SCORE:          {result['score']}")
        return

    print(f"    CMM:            {result['cmm']:.4f}")
    print(f"    clusters found: {result['n_clusters']}  (true k = {result['true_k']})")
    print(f"    noise fraction: {result['noise_frac']:.4f}")
    print(f"    count penalty:  {result['count_penalty']:.4f}  "
          f"(weight={args.count_penalty_weight})")
    print(f"    ------------------------------------")
    print(f"    SCORE:          {result['score']:.4f}")


if __name__ == '__main__':
    main()
