"""
Main entry point for running and experimenting with CEDGM
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
    from baseframework.metrics.TSindex import tempsil
except ImportError:
    print("Warning: Could not import metrics!")

# old form denstream
def _evaluate(X_acc, y_acc, labels_acc, ts_acc):
    """Compute and print CMM and Temporal Silhouette on accumulated data."""
    labels_arr = np.array(labels_acc)
    unique_clusters = np.unique(labels_arr[labels_arr != -1])
    if len(unique_clusters) < 2:
        print("   [Eval] Skipped: fewer than 2 non-noise clusters found.")
        return

    w = np.ones(len(X_acc))
    cmm = get_cmm(np.array(X_acc), np.array(y_acc), labels_arr, w, k=5)
    _, _, ts = tempsil(np.array(ts_acc), np.array(X_acc), labels_arr)
    print(f"   [Eval] CMM={cmm:.4f}  |  TS={ts:.4f}  |  "
          f"n={len(labels_arr)}  k={len(unique_clusters)}")


def main():
    parser = argparse.ArgumentParser(description="Run CEDGM Clustering Simulation")

    # dataset / batching
    parser.add_argument('--dataset', type=str, default='complex9',
                        help='Dataset name: complex9, rbf3, har, stream_densired')
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

    # evaluation frequency
    parser.add_argument('--eval_interval', type=int, default=1,
                        help='Run evaluation every N batches (0 = only at end of stream)')

    args = parser.parse_args()

    print(f"Loading data '{args.dataset}'...")
    X, y = load_data(args.dataset)

    # initialize CEDGM
    cedgm = CEDGM(
        radius=args.radius,
        min_threshold=args.min_threshold,
        decay=args.decay,
        cell_size=args.cell_size 
    )
    

    num_batches = len(X) // args.batch_size

    print(f"\n=======================================================")
    print(f"STARTING CEDGM STREAM PROCESSING: {num_batches} batches of size {args.batch_size}")
    print(f"PARAMETERS: radius={args.radius}  min_threshold={args.min_threshold}  "
          f"decay={args.decay}  cell_size={args.cell_size}")
    print(f"=======================================================\n")


    all_X, all_assignments, all_ts = [], [], []

    for i in range(num_batches + 1):
        start_idx = i * args.batch_size
        end_idx = min((i + 1) * args.batch_size, len(X))
        batch = X[start_idx:end_idx]

        if len(batch) == 0:
            break

        #  logical timestamps based on the points_per_timestep parameter
        # example: if points_per_timestep=10, points 0-9 get t=0, points 10-19 get t=1, etc..
        timestamps = np.arange(start_idx, end_idx) // args.points_per_timestep

        # ONLINE PHASE
        results = cedgm.learn(batch, timestamps)
        
        # summary_id represents the ID of the CMC or Outlier the point was absorbed into
        batch_assignments = [r[0] for r in results]

        all_X.extend(batch)
        all_assignments.extend(batch_assignments)
        all_ts.extend(timestamps)

        print(f"   Batch {i:>4d} | points so far: {len(all_X):>6d} | Current Time (t): {timestamps[-1]}")

        # Graph tracking
        run_eval = (
            args.eval_interval > 0 and (i + 1) % args.eval_interval == 0
        )
        if run_eval:
            cluster_dict = cedgm.predict()
            labels = [cluster_dict.get(a, -1) for a in batch_assignments]
            num_clusters = len(np.unique(np.array(labels)[np.array(labels) != -1]))
            print(f"          [Live Graph] Active Macro-Clusters tracking: {num_clusters}")
            
            # _evaluate(list(batch), list(y[start_idx:end_idx]), labels, list(timestamps))

        print(f"\n--- Stream Finished ---")
        print(f"    Total points: {len(all_X)}")

if __name__ == '__main__':
    main()