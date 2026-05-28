"""
programmatic hyperparameter search for CEDGM.

A search here is three decoupled pieces:
  1. candidate generation   grid_candidates / random_candidates  -> yields {param: value}
  2. evaluation             evaluate_params (from run_cedgm)      -> one score per config
  3. ranking + reporting    run_search                           -> all results, best first

To add a new strategy (e.g. Bayesian search), write another generator that yields
{param: value} dicts and hand it to run_search. Steps 2 and 3 stay unchanged.

Run from the project root, e.g.:
    uv run python tuning.py --dataset complex9 --method grid
    uv run python tuning.py --dataset complex9 --method random --n_iter 40
"""

import sys
sys.path.insert(0, '.')

import argparse
import itertools
import numpy as np

from run_cedgm import evaluate_params
from baseframework.datahandler import load_data

def grid_candidates(param_grid, constraint=None):
    """Yield every combination on the mesh `param_grid` (name -> list of values).

    Combinations rejected by `constraint(params) -> bool` are skipped, so e.g.
    the `cell_size >= radius` rule keeps the grid to the meaningful region.
    """
    names = list(param_grid)
    for combo in itertools.product(*param_grid.values()):
        params = dict(zip(names, combo))
        if constraint is None or constraint(params):
            yield params

def random_candidates(param_space, n_iter, *, seed=None, constraint=None):
    """Yield up to `n_iter` random configs.

    `param_space` maps each name to a sampler `rng -> value`, so any
    distribution is expressed inline (uniform, log-uniform, integer, ...).
    """
    rng = np.random.default_rng(seed)
    produced = 0
    # cap attempts so a very tight constraint can never loop forever
    for _ in range(n_iter * 100):
        if produced >= n_iter:
            break
        params = {name: sample(rng) for name, sample in param_space.items()}
        if constraint is None or constraint(params):
            yield params
            produced += 1

def run_search(X, y, candidates, *, fixed=None, count_penalty_weight=0.5, verbose=True):
    """Evaluate each candidate config and return all results sorted best-first.

    `fixed` holds parameters kept constant; it is merged into every candidate, so
    together the searched + fixed params must cover radius, min_threshold, decay
    and cell_size (what evaluate_params needs).
    """
    fixed = fixed or {}
    results = []
    for params in candidates:
        res = evaluate_params(X, y, count_penalty_weight=count_penalty_weight,
                              **{**fixed, **params})
        results.append(res)
        if verbose:
            print(format_result(res))
    results.sort(key=lambda r: r["score"], reverse=True)
    return results

def format_result(res):
    """One-line summary of a single evaluation."""
    p = res["params"]
    cmm = f"{res['cmm']:.4f}" if res["valid"] else " n/a  "
    return (f"  radius={p['radius']:.3f}  cell_size={p['cell_size']:.3f}  "
            f"min_thr={p['min_threshold']:.1f}  decay={int(p['decay']):>4d}  ->  "
            f"score={res['score']:>9.4f}  (cmm={cmm}, k={res['n_clusters']})")

def print_top(results, n=5):
    """Print the best `n` configurations."""
    print(f"\n=== Top {n} configurations ===")
    for rank, res in enumerate(results[:n], 1):
        print(f"{rank:>2d}.{format_result(res)}")
    best = results[0]
    print(f"\nBest score: {best['score']:.4f}  with {best['params']}")

def grid_matrix(results, x_param, y_param, metric="score"):
    """Pivot 2-D grid results into (x_values, y_values, matrix[row=y, col=x])."""
    xs = sorted({r["params"][x_param] for r in results})
    ys = sorted({r["params"][y_param] for r in results})
    lut = {(r["params"][x_param], r["params"][y_param]): r for r in results}
    M = np.full((len(ys), len(xs)), np.nan)
    for j, yv in enumerate(ys):
        for i, xv in enumerate(xs):
            r = lut.get((xv, yv))
            if r is not None:
                M[j, i] = r[metric]
    return xs, ys, M

def grid_matrix_marginalized(results, x_param, y_param, metric="score", agg=max):
    """Pivot N-D results to a 2-D matrix, aggregating across all other axes.

    For the refined grid we vary 4 params; to project that onto a (radius,
    cell_size) heatmap, each cell shows the *best* score across all sampled combinations
    """
    xs = sorted({r["params"][x_param] for r in results})
    ys = sorted({r["params"][y_param] for r in results})
    buckets = {}
    for r in results:
        key = (r["params"][x_param], r["params"][y_param])
        buckets.setdefault(key, []).append(r[metric])
    M = np.full((len(ys), len(xs)), np.nan)
    for j, yv in enumerate(ys):
        for i, xv in enumerate(xs):
            vals = buckets.get((xv, yv))
            if vals:
                M[j, i] = agg(vals)
    return xs, ys, M


def print_matrix(xs, ys, M, x_param, y_param, metric):
    """Console heatmap — always available, no dependencies."""
    print(f"\n{metric} over {x_param} (cols) x {y_param} (rows):")
    print("        " + "".join(f"{x:>8.3f}" for x in xs))
    for j, yv in enumerate(ys):
        row = "".join("     .  " if np.isnan(v) else f"{v:>8.3f}" for v in M[j])
        print(f"{yv:>7.3f} {row}")

def save_heatmap(xs, ys, M, x_param, y_param, metric, path):
    """Save a heatmap PNG. Needs matplotlib (optional); skips cleanly if absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("   [plot skipped] matplotlib not installed — run "
              "`uv pip install matplotlib` for the PNG (the table above still shows the grid).")
        return None

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(M, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(xs)), [f"{x:.3g}" for x in xs])
    ax.set_yticks(range(len(ys)), [f"{y:.3g}" for y in ys])
    ax.set_xlabel(x_param)
    ax.set_ylabel(y_param)
    ax.set_title(f"CEDGM {metric}")
    fig.colorbar(im, ax=ax, label=metric)
    for j in range(len(ys)):
        for i in range(len(xs)):
            if not np.isnan(M[j, i]):
                ax.text(i, j, f"{M[j, i]:.2f}", ha="center", va="center",
                        color="white", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"   heatmap saved to {path}")
    return path

def main():
    parser = argparse.ArgumentParser(description="Hyperparameter search for CEDGM")
    parser.add_argument('--dataset', default='complex9',
                        help='Dataset name: complex9, rbf3, har, stream_densired, spiral')
    parser.add_argument('--method', choices=['grid', 'random', 'refined'], default='grid',
                        help='grid: 2-D coarse mesh; random: 4-D random samples; '
                             'refined: 4-D grid seeded from the random search top-5')
    parser.add_argument('--n_iter', type=int, default=40,
                        help='Number of configs to try (random search only)')
    parser.add_argument('--count_penalty_weight', type=float, default=0.5,
                        help='Weight of the |n_clusters - true_k| penalty in the score')
    parser.add_argument('--seed', type=int, default=0,
                        help='RNG seed for random search (reproducibility)')
    parser.add_argument('--plot', default='data/tuning_heatmap.png',
                        help='Where to save the grid heatmap PNG (grid method only)')
    args = parser.parse_args()

    print(f"Loading data '{args.dataset}'...")
    X, y = load_data(args.dataset)

    # cell_size below radius makes the grid miss merge candidates -> over-segmentation
    constraint = lambda p: p['cell_size'] >= p['radius']

    if args.method == 'grid':
        # 2-D grid over the two dominant spatial params; others held fixed.
        param_grid = {
            'radius':    [0.05, 0.10, 0.15, 0.20, 0.25],
            'cell_size': [0.10, 0.15, 0.20, 0.25, 0.30],
        }
        fixed = {'min_threshold': 5.0, 'decay': 100}
        candidates = list(grid_candidates(param_grid, constraint))
        print(f"\nGRID SEARCH on '{args.dataset}': {len(candidates)} configs "
              f"(min_threshold/decay fixed at {fixed})\n")
        results = run_search(X, y, candidates, fixed=fixed,
                             count_penalty_weight=args.count_penalty_weight)

        xs, ys, M = grid_matrix(results, 'radius', 'cell_size', metric='score')
        print_matrix(xs, ys, M, 'radius', 'cell_size', 'score')
        save_heatmap(xs, ys, M, 'radius', 'cell_size', 'score', args.plot)

    elif args.method == 'random':
        param_space = {
            'radius':        lambda rng: round(rng.uniform(0.03, 0.30), 4),
            'cell_size':     lambda rng: round(rng.uniform(0.05, 0.30), 4),
            'min_threshold': lambda rng: round(rng.uniform(2, 30), 1),
            'decay':         lambda rng: int(rng.integers(50, 1000)),
        }
        print(f"\nRANDOM SEARCH on '{args.dataset}': {args.n_iter} configs "
              f"(seed={args.seed})\n")
        candidates = random_candidates(param_space, args.n_iter,
                                       seed=args.seed, constraint=constraint)
        results = run_search(X, y, candidates,
                             count_penalty_weight=args.count_penalty_weight)

    else:  # refined
        param_grid = {
            'radius':        [0.08, 0.10, 0.12],
            'cell_size':     [0.15, 0.20, 0.25],
            'min_threshold': [20.0, 25.0, 30.0],
            'decay':         [500, 700, 900],
        }
        candidates = list(grid_candidates(param_grid, constraint))
        print(f"\nREFINED 4-D GRID on '{args.dataset}': {len(candidates)} configs\n")
        results = run_search(X, y, candidates,
                             count_penalty_weight=args.count_penalty_weight)

        xs, ys, M = grid_matrix_marginalized(results, 'radius', 'cell_size', metric='score')
        print_matrix(xs, ys, M, 'radius', 'cell_size', 'best score (max over min_thr, decay)')
        refined_path = args.plot.replace('.png', '_refined.png')
        save_heatmap(xs, ys, M, 'radius', 'cell_size', 'best score', refined_path)

    print_top(results, n=5)


if __name__ == '__main__':
    main()
