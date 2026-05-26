import { useState, useEffect, useRef } from "react";
import Controls from "./Controls";
import Visualization from "./Visualization";
import "./App.css";

const DEFAULT_PARAMS = {
  dataset: "complex9",
  radius: 20,
  min_threshold: 5,
  decay: 200,
  cell_size: 15,
};

export default function App() {
  const [mode, setMode] = useState("batch"); // "batch" | "stream"
  const [params, setParams] = useState(DEFAULT_PARAMS);

  // Batch state
  const [batchResult, setBatchResult] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [error, setError] = useState(null);

  // Stream state
  const [frames, setFrames] = useState([]);
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [streamDone, setStreamDone] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [batchSize, setBatchSize] = useState(20);
  const [streamBounds, setStreamBounds] = useState(null); // locked on first frame
  const abortRef = useRef(null);

  // ── Batch run ──────────────────────────────────────────────
  async function runBatch() {
    setBatchLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
      setBatchResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setBatchLoading(false);
    }
  }

  // ── Stream fetch ───────────────────────────────────────────
  async function startStream() {
    // cancel any running stream
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setFrames([]);
    setFrameIdx(0);
    setStreamDone(false);
    setStreamBounds(null);
    setError(null);
    setStreaming(true);
    setPlaying(true);

    try {
      // Fetch full-dataset bounds before streaming so the grid is correctly
      // sized from the first frame and never needs to resize mid-stream.
      const boundsRes = await fetch(
        `http://localhost:8000/bounds?dataset=${encodeURIComponent(params.dataset)}`,
        { signal: ctrl.signal },
      );
      if (!boundsRes.ok) throw new Error((await boundsRes.json()).detail ?? boundsRes.statusText);
      setStreamBounds(await boundsRes.json());

      const res = await fetch("http://localhost:8000/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...params, batch_size: batchSize }),
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop();
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const frame = JSON.parse(part.slice(6));
          if (frame.done) { setStreamDone(true); setPlaying(false); break; }
          setFrames(prev => [...prev, frame]);
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
    } finally {
      setStreaming(false);
    }
  }

  function stopStream() {
    abortRef.current?.abort();
    setPlaying(false);
    setStreaming(false);
  }

  function resetStream() {
    stopStream();
    setFrames([]);
    setFrameIdx(0);
    setStreamDone(false);
  }

  // ── Playback loop ──────────────────────────────────────────
  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setFrameIdx(idx => {
        if (idx + 1 >= frames.length) {
          if (streamDone) setPlaying(false);
          return idx; // wait for more frames
        }
        return idx + 1;
      });
    }, 1000 / speed);
    return () => clearInterval(id);
  }, [playing, speed, frames.length, streamDone]);

  // ── Derived display data ───────────────────────────────────
  const currentFrame = frames[frameIdx] ?? null;
  const vizData = mode === "batch" ? batchResult : currentFrame;
  const currentT = currentFrame?.t ?? null;
  const totalT   = currentFrame?.n_total ?? frames[frames.length - 1]?.n_total ?? null;

  const nCmcs = vizData?.mc_states?.filter(m => m.is_core).length ?? 0;
  const nOmcs = vizData?.mc_states?.filter(m => !m.is_core).length ?? 0;

  return (
    <div className="app">
      <header>
        <h1>CEDGM Visualizer</h1>
        {vizData && (
          <div className="stats-inline">
            {mode === "batch" && <span>{batchResult.n_points.toLocaleString()} points</span>}
            {mode === "stream" && currentT && <span>t = {currentT.toLocaleString()} / {totalT?.toLocaleString()}</span>}
            <span className="stat-sep">·</span>
            <span>{nCmcs} CMCs</span>
            <span className="stat-sep">·</span>
            <span>{nOmcs} OMCs</span>
          </div>
        )}
      </header>

      {/* Mode toggle */}
      <div className="mode-tabs">
        <button
          className={`mode-tab ${mode === "batch" ? "active" : ""}`}
          onClick={() => setMode("batch")}
        >Batch</button>
        <button
          className={`mode-tab ${mode === "stream" ? "active" : ""}`}
          onClick={() => setMode("stream")}
        >Stream</button>
      </div>

      <div className="viz-card">
        <Visualization
          data={vizData}
          loading={mode === "batch" ? batchLoading : false}
          currentT={mode === "stream" ? currentT : null}
          totalT={mode === "stream" ? totalT : null}
          fixedBounds={mode === "stream" ? streamBounds : (batchResult?.bounds ?? null)}
        />
      </div>

      <div className="controls-card">
        <Controls
          mode={mode}
          params={params}
          setParams={setParams}
          speed={speed}
          setSpeed={setSpeed}
          batchSize={batchSize}
          setBatchSize={setBatchSize}
          playing={playing}
          streaming={streaming}
          streamDone={streamDone}
          frameIdx={frameIdx}
          totalFrames={frames.length}
          onRunBatch={runBatch}
          onStartStream={startStream}
          onPlayPause={() => setPlaying(p => !p)}
          onStop={stopStream}
          onReset={resetStream}
          onSeek={setFrameIdx}
          loading={batchLoading}
        />
        {error && <p className="error">Error: {error}</p>}
      </div>
    </div>
  );
}
