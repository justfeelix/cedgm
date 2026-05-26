from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import numpy as np
import json
import os

from src.cedgm import CEDGM

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"

DATASETS = {
    "complex9":        ("complex9_data.npy",        "complex9_label.npy"),
    "HAR":             ("HAR_data.npy",              "HAR_label.npy"),
    "rbf3":            ("rbf3_data.npy",             "rbf3_label.npy"),
    "stream_densired": ("stream_densired_data.npy",  "stream_densired_label.npy"),
}


def load_dataset(key: str) -> tuple[np.ndarray, np.ndarray]:
    if key not in DATASETS:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {key}")
    data_file, label_file = DATASETS[key]
    data   = np.load(os.path.join(DATA_DIR, data_file))
    labels = np.load(os.path.join(DATA_DIR, label_file))
    return data, labels


class RunParams(BaseModel):
    dataset: str = "complex9"
    radius: float = 0.5
    min_threshold: float = 3.0
    decay: int = 100
    cell_size: float = 0.5


class StreamParams(RunParams):
    batch_size: int = 20


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/datasets")
def list_datasets():
    return {"datasets": list(DATASETS.keys())}


@app.get("/bounds")
def get_bounds(dataset: str):
    data, _ = load_dataset(dataset)
    col0, col1 = data[:, 0], data[:, 1]
    x0, x1 = float(col0.min()), float(col0.max())
    y0, y1 = float(col1.min()), float(col1.max())
    xpad = (x1 - x0) * 0.07 or 1.0
    ypad = (y1 - y0) * 0.07 or 1.0
    return {"x0": x0 - xpad, "x1": x1 + xpad, "y0": y0 - ypad, "y1": y1 + ypad}


@app.post("/run")
def run(params: RunParams):
    data, ground_truth = load_dataset(params.dataset)

    cedgm = CEDGM(
        radius=params.radius,
        min_threshold=params.min_threshold,
        decay=params.decay,
        cell_size=params.cell_size,
    )

    events = []
    for t, point in enumerate(data):
        mc_id, cluster_id, log = cedgm.learn_one(point, t=t)
        events.append({"t": t, "mc_id": mc_id, "cluster_id": cluster_id, "log": log})

    labels = cedgm.predict()
    mc_states = []
    for mc_id, mc in {**cedgm.cmcs, **cedgm.outliers}.items():
        mc_states.append({
            "mc_id": mc_id,
            "center": mc.center.tolist(),
            "density": mc.density,
            "life": mc.life,
            "kernel_radius": mc.get_kernel_radius(),
            "cluster_label": labels.get(mc_id, -1),
            "is_core": mc_id in cedgm.cmcs,
        })

    col0, col1 = data[:, 0], data[:, 1]
    x0, x1 = float(col0.min()), float(col0.max())
    y0, y1 = float(col1.min()), float(col1.max())
    xpad = (x1 - x0) * 0.07 or 1.0
    ypad = (y1 - y0) * 0.07 or 1.0

    return {
        "mc_states": mc_states,
        "events": events,
        "n_points": len(data),
        "ground_truth": ground_truth.tolist(),
        "bounds": {"x0": x0 - xpad, "x1": x1 + xpad, "y0": y0 - ypad, "y1": y1 + ypad},
    }


def _mc_states(cedgm) -> list:
    labels = cedgm.predict()
    return [
        {
            "mc_id": mc_id,
            "center": mc.center.tolist(),
            "density": mc.density,
            "life": mc.life,
            "kernel_radius": mc.get_kernel_radius(),
            "cluster_label": labels.get(mc_id, -1),
            "is_core": mc_id in cedgm.cmcs,
        }
        for mc_id, mc in {**cedgm.cmcs, **cedgm.outliers}.items()
    ]


@app.post("/stream")
def stream(params: StreamParams):
    data, _ = load_dataset(params.dataset)
    n = len(data)

    def generate():
        cedgm = CEDGM(
            radius=params.radius,
            min_threshold=params.min_threshold,
            decay=params.decay,
            cell_size=params.cell_size,
        )
        batch_events = []
        for t, point in enumerate(data):
            _, _, log = cedgm.learn_one(point, t=t)
            batch_events.append(log)

            if (t + 1) % params.batch_size == 0 or t == n - 1:
                frame = {
                    "t": t + 1,
                    "n_total": n,
                    "mc_states": _mc_states(cedgm),
                    "events": batch_events,
                }
                yield f"data: {json.dumps(frame)}\n\n"
                batch_events = []

        yield 'data: {"done": true}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
