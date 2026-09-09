import { useMemo } from "react";
import type { Cell, DrainNode, Route } from "../types";

const W = 48, H = 36, CS = 14;
const WIDTH = W * CS, HEIGHT = H * CS;

function depthColor(d: number): string {
  if (d < 1) return "#eef3f4";
  if (d < 8) return "#cfe7ec";
  if (d < 16) return "#8fcdd9";
  if (d < 28) return "#3fb0c4";
  if (d < 45) return "#177fa3";
  return "#0b4f77";
}
function rainColor(m: number): string {
  if (m < 8) return "#eef3f4";
  if (m < 24) return "#dbe6fb";
  if (m < 45) return "#a9c2f0";
  if (m < 70) return "#5c85d6";
  return "#274fb0";
}

export default function FloodMap({ cells, routes, nodes, mode }: {
  cells: Cell[]; routes: Route[]; nodes?: DrainNode[]; mode: "depth" | "rain";
}) {
  const cellMap = useMemo(() => {
    const m = new Map<number, Cell>();
    cells.forEach((c) => m.set(c.y * W + c.x, c));
    return m;
  }, [cells]);

  const rects = [];
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const c = cellMap.get(y * W + x);
      if (!c) continue;
      const fill = mode === "depth" ? depthColor(c.depth_cm) : rainColor(c.mmh);
      rects.push(<rect key={`${x}-${y}`} x={x * CS} y={y * CS} width={CS} height={CS}
        fill={fill} stroke="#ffffff" strokeWidth={0.6} />);
    }
  }

  const paths = routes.filter((r) => r.path && r.path.length).map((r) => {
    const pts = r.path.map((p) => `${p.x * CS + CS / 2},${p.y * CS + CS / 2}`).join(" ");
    const col = r.mode === "flood-safe" ? "#10a37f" : "#e05d5d";
    const w = r.mode === "flood-safe" ? 3 : 2;
    return <polyline key={r.mode} points={pts} fill="none" stroke={col} strokeWidth={w}
      strokeLinecap="round" strokeLinejoin="round" />;
  });

  const nodeDots = (nodes || []).map((n) => (
    <circle key={`${n.ix}-${n.iy}`} cx={n.x * CS + CS / 2} cy={n.y * CS + CS / 2} r={2}
      fill={n.surcharge_m3min > 0 ? "#e05d5d" : "#2b6f8f"} opacity={0.7} />
  ));

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="map" style={{ width: "100%", height: "auto" }}>
      {rects}
      {paths}
      {nodeDots}
    </svg>
  );
}
