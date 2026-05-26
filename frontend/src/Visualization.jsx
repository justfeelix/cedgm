import { useState, useMemo } from "react";

const VB_W = 760;
const VB_H = 480;
const M = { top: 20, right: 24, bottom: 48, left: 58 };
const IW = VB_W - M.left - M.right;
const IH = VB_H - M.top - M.bottom;

const COLORS = [
  "#007A4D","#005c39","#3a9e6f","#e37222","#a2ad00",
  "#007c92","#9b0600","#f0c040","#6ab090","#c8102e",
  "#4c9b6e","#e07b39","#00843D","#8b2fc9","#6a9b2f",
];

function clusterColor(label) {
  if (label < 0) return null;
  return COLORS[label % COLORS.length];
}

function niceTicks(min, max, n = 6) {
  const range = max - min || 1;
  const raw = range / n;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(f => f * mag).find(s => s >= raw) ?? mag;
  const start = Math.ceil(min / step) * step;
  const ticks = [];
  for (let t = start; t <= max + 1e-9; t = parseFloat((t + step).toFixed(12)))
    ticks.push(parseFloat(t.toFixed(10)));
  return ticks;
}

function fmt(v) {
  if (Math.abs(v) >= 1000) return v.toFixed(0);
  if (Math.abs(v) >= 10)   return v.toFixed(1);
  return v.toFixed(2);
}

export default function Visualization({ data, loading, currentT, totalT, fixedBounds }) {
  const [tooltip, setTooltip] = useState(null);

  const derived = useMemo(() => {
    if (!data?.mc_states?.length) return null;
    const mc = data.mc_states;

    let x0, x1, y0, y1;
    if (fixedBounds) {
      ({ x0, x1, y0, y1 } = fixedBounds);
    } else {
      const xs = mc.map(m => m.center[0]);
      const ys = mc.map(m => m.center[1]);
      x0 = Math.min(...xs); x1 = Math.max(...xs);
      y0 = Math.min(...ys); y1 = Math.max(...ys);
      const xSpan = Math.max(x1 - x0, Math.abs(x1 + x0) * 0.1 || 1);
      const ySpan = Math.max(y1 - y0, Math.abs(y1 + y0) * 0.1 || 1);
      x0 -= xSpan * 0.07; x1 += xSpan * 0.07;
      y0 -= ySpan * 0.07; y1 += ySpan * 0.07;
    }

    const maxDensity = Math.max(...mc.map(m => m.density));
    const scaleX = x => M.left + ((x - x0) / (x1 - x0)) * IW;
    const scaleY = y => M.top + IH - ((y - y0) / (y1 - y0)) * IH;

    const points = mc.map(m => ({
      ...m,
      cx: scaleX(m.center[0]),
      cy: scaleY(m.center[1]),
      r: Math.max(5, Math.sqrt(m.density / maxDensity) * 22),
    }));

    return { points, x0, x1, y0, y1, scaleX, scaleY };
  }, [data, fixedBounds]);

  if (!data && !loading) return (
    <div className="empty-plot">
      <p>Configure parameters below and press <strong>Run Algorithm</strong> or <strong>Start</strong>.</p>
    </div>
  );

  if (loading) return (
    <div className="empty-plot">
      <p className="loading-text">Processing stream…</p>
    </div>
  );

  const { points, x0, x1, y0, y1, scaleX, scaleY } = derived;
  const xTicks = niceTicks(x0, x1);
  const yTicks = niceTicks(y0, y1);

  const cmcs = points.filter(p => p.is_core);
  const omcs = points.filter(p => !p.is_core);

  return (
    <div className="viz-wrap">
      {/* Progress bar */}
      {currentT != null && totalT != null && (
        <div className="progress-bar-wrap">
          <div className="progress-bar" style={{ width: `${(currentT / totalT) * 100}%` }} />
          <span className="progress-label">t = {currentT.toLocaleString()} / {totalT.toLocaleString()}</span>
        </div>
      )}

      <svg
        className="viz-svg"
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        onMouseLeave={() => setTooltip(null)}
      >
        <rect x={M.left} y={M.top} width={IW} height={IH} fill="#f4faf7" />

        {xTicks.map(t => (
          <line key={`gx${t}`} x1={scaleX(t)} y1={M.top} x2={scaleX(t)} y2={M.top + IH}
            stroke="#c5dfd0" strokeWidth="1" />
        ))}
        {yTicks.map(t => (
          <line key={`gy${t}`} x1={M.left} y1={scaleY(t)} x2={M.left + IW} y2={scaleY(t)}
            stroke="#c5dfd0" strokeWidth="1" />
        ))}

        <rect x={M.left} y={M.top} width={IW} height={IH}
          fill="none" stroke="#8ecbac" strokeWidth="1.5" />

        {xTicks.map(t => (
          <g key={`xt${t}`}>
            <line x1={scaleX(t)} y1={M.top + IH} x2={scaleX(t)} y2={M.top + IH + 6}
              stroke="#7aab93" strokeWidth="1" />
            <text x={scaleX(t)} y={M.top + IH + 19}
              textAnchor="middle" fontSize="12" fill="#4a7a62" fontFamily="system-ui">
              {fmt(t)}
            </text>
          </g>
        ))}

        {yTicks.map(t => (
          <g key={`yt${t}`}>
            <line x1={M.left - 6} y1={scaleY(t)} x2={M.left} y2={scaleY(t)}
              stroke="#7aab93" strokeWidth="1" />
            <text x={M.left - 10} y={scaleY(t) + 4}
              textAnchor="end" fontSize="12" fill="#4a7a62" fontFamily="system-ui">
              {fmt(t)}
            </text>
          </g>
        ))}

        {omcs.map(p => (
          <circle key={`o${p.mc_id}`}
            cx={p.cx} cy={p.cy} r={p.r}
            fill="#7aab93" fillOpacity={0.28}
            stroke="#4a7a62" strokeWidth="1" strokeOpacity={0.5}
            style={{ cursor: "pointer" }}
            onMouseEnter={() => setTooltip(p)}
          />
        ))}

        {cmcs.map(p => {
          const col = clusterColor(p.cluster_label) ?? "#007A4D";
          return (
            <circle key={`c${p.mc_id}`}
              cx={p.cx} cy={p.cy} r={p.r}
              fill={col} fillOpacity={0.72}
              stroke={col} strokeWidth="1.5"
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setTooltip(p)}
            />
          );
        })}

        {tooltip && (() => {
          const { cx, cy } = tooltip;
          const bw = 148, bh = 92, pad = 10;
          const bx = cx + bw + pad > VB_W - M.right ? cx - bw - pad : cx + pad;
          const by = Math.max(M.top, Math.min(cy - bh / 2, M.top + IH - bh));
          return (
            <g style={{ pointerEvents: "none" }}>
              <rect x={bx} y={by} width={bw} height={bh} rx={6}
                fill="#003825" fillOpacity={0.92} />
              {[
                ["ID",      tooltip.mc_id],
                ["Cluster", tooltip.cluster_label],
                ["Density", tooltip.density.toFixed(3)],
                ["Life",    tooltip.life.toFixed(3)],
                ["KernelR", tooltip.kernel_radius.toFixed(3)],
              ].map(([k, v], i) => (
                <text key={k} x={bx + 10} y={by + 16 + i * 15}
                  fontSize="12" fill="#eef6f1" fontFamily="system-ui">
                  <tspan fill="#6ab090">{k}: </tspan>{v}
                </text>
              ))}
            </g>
          );
        })()}
      </svg>

    </div>
  );
}
