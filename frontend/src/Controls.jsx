import { useState, useEffect } from "react";

const DATASET_PRESETS = {
  complex9:        { radius: 20,   min_threshold: 5,  decay: 200, cell_size: 15   },
  rbf3:            { radius: 0.06, min_threshold: 3,  decay: 100, cell_size: 0.05 },
  stream_densired: { radius: 2.5,  min_threshold: 3,  decay: 150, cell_size: 2    },
};

const ALGO_SLIDERS = [
  { key: "radius",        label: "Radius",        min: 0.01, max: 100,  step: 0.01, dec: 2 },
  { key: "min_threshold", label: "Min Threshold", min: 0.5,  max: 30,   step: 0.5,  dec: 1 },
  { key: "decay",         label: "Decay",         min: 10,   max: 1000, step: 10,   dec: 0 },
  { key: "cell_size",     label: "Cell Size",     min: 0.01, max: 50,   step: 0.01, dec: 2 },
];

const DATASETS_2D = ["complex9", "rbf3", "stream_densired"];

export default function Controls({
  mode, params, setParams,
  speed, setSpeed, batchSize, setBatchSize,
  playing, streaming, streamDone, frameIdx, totalFrames,
  onRunBatch, onStartStream, onPlayPause, onStop, onReset, onSeek,
  loading,
}) {
  const [datasets, setDatasets] = useState(DATASETS_2D);

  useEffect(() => {
    fetch("http://localhost:8000/datasets")
      .then(r => r.json())
      .then(d => setDatasets(d.datasets.filter(k => DATASETS_2D.includes(k))))
      .catch(() => {});
  }, []);

  function handleDatasetChange(ds) {
    setParams({ ...params, dataset: ds, ...(DATASET_PRESETS[ds] ?? {}) });
  }

  const disabled = loading || streaming;

  return (
    <div className="controls">
      {/* Dataset */}
      <div className="ctrl-group">
        <label className="ctrl-label">Dataset</label>
        <select
          className="ctrl-select"
          value={params.dataset}
          onChange={e => handleDatasetChange(e.target.value)}
          disabled={disabled}
        >
          {datasets.map(ds => <option key={ds} value={ds}>{ds}</option>)}
        </select>
      </div>

      <div className="ctrl-divider" />

      {/* Algorithm sliders */}
      {ALGO_SLIDERS.map(({ key, label, min, max, step, dec }) => {
        const val = params[key];
        const display = dec === 0 ? String(val) : Number(val).toFixed(dec);
        return (
          <div className="ctrl-group" key={key}>
            <div className="ctrl-header">
              <label className="ctrl-label">{label}</label>
              <span className="ctrl-value">{display}</span>
            </div>
            <input
              className="ctrl-slider"
              type="range" min={min} max={max} step={step} value={val}
              disabled={disabled}
              onChange={e => setParams({
                ...params,
                [key]: dec === 0 ? parseInt(e.target.value) : parseFloat(e.target.value),
              })}
              onDoubleClick={() => {
                const def = DATASET_PRESETS[params.dataset]?.[key];
                if (def !== undefined) setParams({ ...params, [key]: def });
              }}
            />
            <div className="ctrl-range-labels"><span>{min}</span><span>{max}</span></div>
          </div>
        );
      })}

      <div className="ctrl-divider" />

      {mode === "batch" ? (
        /* ── Batch mode ── */
        <button className="run-btn" onClick={onRunBatch} disabled={loading}>
          {loading ? <><span className="spinner" /> Running…</> : "Run Algorithm"}
        </button>
      ) : (
        /* ── Stream mode ── */
        <div className="stream-controls">
          {/* Speed */}
          <div className="ctrl-group">
            <div className="ctrl-header">
              <label className="ctrl-label">Speed</label>
              <span className="ctrl-value">{speed} fps</span>
            </div>
            <input
              className="ctrl-slider"
              type="range" min={1} max={60} step={1} value={speed}
              onChange={e => setSpeed(parseInt(e.target.value))}
            />
            <div className="ctrl-range-labels"><span>1</span><span>60</span></div>
          </div>

          {/* Batch size */}
          <div className="ctrl-group">
            <div className="ctrl-header">
              <label className="ctrl-label">Pts / Frame</label>
              <span className="ctrl-value">{batchSize}</span>
            </div>
            <input
              className="ctrl-slider"
              type="range" min={1} max={200} step={1} value={batchSize}
              disabled={streaming}
              onChange={e => setBatchSize(parseInt(e.target.value))}
            />
            <div className="ctrl-range-labels"><span>1</span><span>200</span></div>
          </div>

          {/* Buttons */}
          <div className="stream-btns">
            <button className="run-btn" onClick={onStartStream} disabled={streaming}>
              {streaming ? <><span className="spinner" /> Loading…</> : "Start"}
            </button>
            <button
              className="run-btn run-btn--secondary"
              onClick={onPlayPause}
              disabled={totalFrames === 0}
            >
              {playing ? "Pause" : "Play"}
            </button>
            <button
              className="run-btn run-btn--ghost"
              onClick={onReset}
              disabled={streaming && !streamDone}
            >
              Reset
            </button>
          </div>

          {/* Scrubber */}
          {totalFrames > 1 && (
            <div className="ctrl-group scrubber">
              <div className="ctrl-header">
                <label className="ctrl-label">Frame</label>
                <span className="ctrl-value">{frameIdx + 1} / {totalFrames}</span>
              </div>
              <input
                className="ctrl-slider"
                type="range" min={0} max={totalFrames - 1} step={1} value={frameIdx}
                onChange={e => { setPlaying(false); onSeek(parseInt(e.target.value)); }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
