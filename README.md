# CEDGM

A stream-clustering algorithm implementation. Data arrives in batches and is
clustered online; macro-clusters are tracked over time.

There are two ways to interact with the project:

- **`run_cedgm.py`** — CLI entry point that streams a dataset through the
  algorithm in batches.
- **`tuning.py`** — programmatic hyperparameter search (grid / random) over the
  CEDGM parameters. See [TUNING.md](TUNING.md) for the approach and reasoning.
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
