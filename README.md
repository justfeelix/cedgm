# CEDGM

A stream-clustering algorithm implementation. Data arrives in batches and is
clustered online; macro-clusters are tracked over time.

There are two ways to interact with the project:

- **`run_cedgm.py`** — CLI entry point that streams a dataset through the
  algorithm in batches.
- **`tuning.py`** — programmatic hyperparameter search (grid / random / refined)
  over the CEDGM parameters.
- **`playground.ipynb`** — notebook for experimentation and visualization.

## Requirements

- **Python ≥ 3.12** — the code uses `from typing import override`.
- Dependencies are pinned in `requirements.txt` (a full freeze including
  `torch`, `matplotlib`, `networkx`, and `clustpy`, which are only needed for
  the notebook).
- For the `run_cedgm.py` CLI specifically, only **numpy, scikit-learn, scipy,
  and pandas** are actually imported.
- The datasets are already present locally as `.npy` files in `data/` (this
  directory is gitignored but the files exist) — no download needed.

> **Note:** Always run from the project root. `datahandler.py` loads data via
> relative paths like `./data/complex9_data.npy`.

## Setup with uv

```bash
cd /path/to/cedgm

# create the venv (3.12+; pin whichever version you have)
uv venv --python 3.12
```

Then install dependencies. Pick one of the following:

**Minimal — CLI only (recommended for running `run_cedgm.py`):**

```bash
uv pip install numpy scikit-learn scipy pandas
```

**Full — matches the pinned freeze (needed for the notebook):**

```bash
uv pip install -r requirements.txt
```

## Running the CLI

```bash
uv run python run_cedgm.py --dataset complex9
```

### Datasets

`complex9` (default), `rbf3`, `har`, `stream_densired`, `spiral`.

### Options

| Flag | Description |
| --- | --- |
| `--dataset` | Dataset name (see above) |
| `--batch_size` | Number of instances per batch |
| `--points_per_timestep` | Data points per logical time step |
| `--radius` | Minimum allowable distance to CMC center |
| `--min_threshold` | Minimum density required to form a CMC |
| `--decay` | Decay parameter (how many past samples matter) |
| `--cell_size` | Physical width of a grid cell (resolution) |
| `--eval_interval` | Run evaluation every N batches (0 = only at end of stream) |

## Hyperparameter tuning

`tuning.py` runs a programmatic search over CEDGM's four main parameters
(`radius`, `cell_size`, `min_threshold`, `decay`).
Each configuration is scored as **CMM minus a cluster-count penalty**, so good clusterings need
both a high CMM and a cluster count close to the true number of classes.

### Three search methods

```bash
# 1. Coarse grid — 2-D mesh over radius × cell_size (the other two params
#    are held at their defaults).
uv run python tuning.py --dataset complex9 --method grid

# 2. Random search — 4-D uniform sampling over all parameters. Use --n_iter
#    to set the budget and --seed for reproducibility.
uv run python tuning.py --dataset complex9 --method random --n_iter 30 --seed 0

# 3. Refined grid — 4-D grid whose ranges are taken from the random search's
#    best region. Run this after random search to verify the best config
uv run python tuning.py --dataset complex9 --method refined
```

### Outputs

Heatmap PNGs land in `data/results/tuning/`:

- `heatmap_coarse.png` — from `--method grid`
- `heatmap_refined.png` — from `--method refined`

Every run also prints the top-5 configurations to the console so you can pick
the winner directly.

### Useful flags

| Flag | Description |
| --- | --- |
| `--dataset` | Dataset name (any of the five built-ins) |
| `--method` | `grid`, `random`, or `refined` |
| `--n_iter` | Configurations to try (random search only) |
| `--seed` | RNG seed for random search (reproducibility) |
| `--count_penalty_weight` | Weight of the cluster-count penalty in the score (default `0.5`) |
| `--plot_dir` | Output directory for heatmap PNGs |

### Suggested order

`grid → random → refined`:

1. **Coarse grid** to localise the good `radius` / `cell_size` region.
2. **Random search** to also tune `min_threshold` and `decay`.
3. **Refined grid** zoomed into the best region from step 2 to check
   robustness and produce a second, finer heatmap.
