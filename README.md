# CEDGM Visualizer

Interactive web tool for visualizing the **CEDGM** stream clustering algorithm in real time.

## Requirements

- Python 3.10+ with `pip` / `uv`
- Node.js 18+

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements_viz.txt
```

Or with `uv`:

```bash
uv pip install -r requirements_viz.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
```

## Running the tool

Open two terminals from the project root.

**Terminal 1 — Backend:**

```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

> If port 5173 is already in use, Vite will pick the next free port and print the actual URL in the terminal output.

## Usage

The tool has two modes, selectable via the tab bar:

### Batch mode

Processes the entire dataset in one go and displays the final clustering result. Adjust the hyperparameters and press **Run Algorithm**.

### Stream mode

Simulates the data stream point by point and animates the evolution of the micro-clusters over time.

1. Set **Pts / Frame** — how many data points are processed per animation frame (lower = more detail, slower)
2. Set **Speed** — playback rate in frames per second
3. Press **Start** — the backend streams all frames in the background while playback begins immediately
4. Use **Play / Pause** to stop and resume the animation
5. Drag the **Frame scrubber** to jump to any point in time
6. Press **Reset** to start over

### Hyperparameters

| Parameter | Description |
|---|---|
| **Radius** | Absorption radius of a micro-cluster |
| **Min Threshold** | Minimum density for an OMC to be promoted to a CMC |
| **Decay** | Decay factor — higher values mean slower decay |
| **Cell Size** | Grid cell size for the spatial index |

Switching datasets automatically loads sensible default values for that dataset.

### Datasets

| Dataset | Points | Notes |
|---|---|---|
| `complex9` | 3 031 | 9 non-convex clusters, good for quick tests |
| `rbf3` | 40 000 | Normalized coordinates (0–1), use small radius |
| `stream_densired` | 10 000 | Mixed densities |

## Project structure

```
├── main.py                  # FastAPI backend (POST /run, POST /stream, GET /datasets)
├── requirements_viz.txt     # Backend dependencies
├── src/
│   ├── cedgm.py             # CEDGM algorithm
│   ├── graph.py             # Macro-cluster graph
│   ├── grid.py              # Spatial index
│   └── micro_clusters.py    # MicroCluster class
├── data/                    # .npy datasets
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main component, mode switching, stream logic
    │   ├── Controls.jsx      # Parameter controls
    │   └── Visualization.jsx # SVG scatter plot
    └── package.json
```
