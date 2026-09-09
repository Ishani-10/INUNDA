import { useEffect, useState } from "react";
import Header from "./components/Header";
import FloodMap from "./components/FloodMap";
import { api } from "./api";
import type { DomainT, FloodResp, RoutesResp, MLResp } from "./types";

type View = "nowcast" | "routes" | "ml";

const G = 48, H = 36, CS = 14;

export default function App() {
  const [view, setView] = useState<View>("nowcast");
  const [domain, setDomain] = useState<DomainT | null>(null);
  const [flood, setFlood] = useState<FloodResp | null>(null);
  const [routes, setRoutes] = useState<RoutesResp | null>(null);
  const [ml, setMl] = useState<MLResp | null>(null);
  const [horizon, setHorizon] = useState(0);
  const [mapMode, setMapMode] = useState<"depth" | "rain">("depth");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>("");

  const reload = async () => {
    setBusy(true);
    try {
      const [d, r, m] = await Promise.all([api.domain(), api.routes(), api.ml()]);
      setDomain(d); setRoutes(r); setMl(m);
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  };

  useEffect(() => { reload(); }, []);

  const loadFlood = async (h: number) => {
    try { setFlood(await api.flood(h)); } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { loadFlood(horizon); }, [horizon]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); await fn().catch((e) => setErr(String(e))); await reload(); setBusy(false);
  };

  const clockStr = (m: number) => `T+${Math.floor(m / 60)}h${String(m % 60).padStart(2, "0")}m`;
  const drains = domain ? Array.from({ length: 130 }, (_, i) => ({
    ix: i % 13, iy: Math.floor(i / 13), x: (i % 13) * 4, y: Math.floor(i / 13) * 4,
    elev: 0, capacity_m3min: 0, inflow_m3min: 0, surcharge_m3min: 0,
  })) : [];

  const floodedCells = flood?.summary.flooded_cells ?? domain?.summary.flooded_cells ?? 0;
  const total = flood?.summary.of ?? domain?.summary.of ?? G * H;

  return (
    <div className="app">
      <Header view={view} setView={(v) => setView(v as View)} revision={domain?.scenario.revision ?? 1}
        ml={ml?.model.trained ?? false} />

      <div className="statusbar">
        <span className="chip">{domain?.scenario.name ?? "…"}</span>
        <span className={"chip " + (domain?.scenario.storm_active ? "storm" : "calm")}>
          {domain?.scenario.storm_active ? "RAIN ON" : "RAIN OFF"}
        </span>
        <span className="chip">{clockStr(domain?.scenario.clock_min ?? 0)}</span>
        <span className="chip">{floodedCells} flooded / {total} cells</span>
        <span className="chip">max {flood?.summary.max_depth_cm ?? domain?.summary.max_depth_cm ?? 0} cm</span>
        <span className="chip msg">{domain?.scenario.events.slice(-1)[0]?.message}</span>
      </div>

      <div className="actions">
        <button disabled={busy} onClick={() => act(() => api.advance(30))}>Advance 30m</button>
        <button disabled={busy} onClick={() => act(() => api.toggle())}>Toggle Rain</button>
        <button disabled={busy} onClick={() => act(() => api.reset())}>Reset</button>
        <label className="slider">
          Lead time: {clockStr(horizon)}
          <input type="range" min={0} max={180} step={30} value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))} />
        </label>
        <div className="legendSwitch">
          <button className={mapMode === "depth" ? "on" : ""} onClick={() => setMapMode("depth")}>Depth</button>
          <button className={mapMode === "rain" ? "on" : ""} onClick={() => setMapMode("rain")}>Rain</button>
        </div>
      </div>

      {err && <div className="error">{err}</div>}

      {view === "nowcast" && (
        <div className="layout">
          <div className="map-panel">
            <div className="legends">
              {mapMode === "depth"
                ? [">45cm","28-45","16-28","8-16","1-8","<1"].map((t, i) => (
                    <span key={t} className="lg"><i style={{ background: ["#0b4f77","#177fa3","#3fb0c4","#8fcdd9","#cfe7ec","#eef3f4"][5-i] }} />{t}</span>))
                : [">70","45-70","24-45","8-24","<8"].map((t, i) => (
                    <span key={t} className="lg"><i style={{ background: ["#274fb0","#5c85d6","#a9c2f0","#dbe6fb","#eef3f4"][4-i] }} />{t} mm/h</span>))}
            </div>
            <FloodMap cells={flood?.cells ?? []} nodes={drains} routes={[]} mode={mapMode} />
          </div>
          <div className="side">
            <h3>Nowcast fields</h3>
            <p>Rain is coupled to terrain and the drain graph to produce a <b>street-level depth</b> forecast. This is the coupled, not isolated-weather, approach.</p>
            <div className="stats">
              <div><b>{flood?.summary.max_depth_cm ?? 0}</b><span>cm max depth</span></div>
              <div><b>{floodedCells}</b><span>flooded cells</span></div>
              <div><b>{flood?.summary.mean_mmh ?? 0}</b><span>mm/h mean rain</span></div>
            </div>
          </div>
        </div>
      )}

      {view === "routes" && (
        <div className="layout">
          <div className="map-panel">
            <FloodMap cells={flood?.cells ?? []} nodes={drains} routes={routes?.routes ?? []} mode="depth" />
          </div>
          <div className="side">
            <h3>Flood-safe routes</h3>
            <p><span className="gs">green</span> = flood-safe · <span className="rs">red</span> = shortest (ignores flood).</p>
            {(routes?.routes ?? []).map((r) => (
              <div key={r.mode} className={"routecard " + (r.mode === "flood-safe" ? "good" : "bad")}>
                <b>{r.mode}</b>
                {r.error ? <span className="err">{r.error}</span> : (
                  <>
                    <span>{r.distance_km} km · max depth {r.max_depth_cm} cm</span>
                    <span>{r.flooded_cells_on_path} flooded cells on path</span>
                    {r.explanations.map((e, i) => <small key={i}>· {e}</small>)}
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {view === "ml" && (
        <div className="layout">
          <div className="map-panel">
            <h3>ML depth surrogate vs baseline</h3>
            <div className="bignum">
              <div><b>{ml?.compare.ml_beats_baseline_pct ?? 0}%</b><span>better than rainfall-threshold baseline</span></div>
            </div>
            <table className="tbl">
              <thead><tr><th></th><th>Hit rate</th><th>False-alarm</th><th>MAE (cm)</th></tr></thead>
              <tbody>
                <tr><td><b>Our ML</b></td><td>{ml?.compare.ml.hit_rate ?? 0}</td><td>{ml?.compare.ml.false_alarm_rate ?? 0}</td><td>{ml?.compare.ml_mae_cm ?? 0}</td></tr>
                <tr><td>Baseline</td><td>{ml?.compare.baseline.hit_rate ?? 0}</td><td>{ml?.compare.baseline.false_alarm_rate ?? 0}</td><td>{ml?.compare.baseline_mae_cm ?? 0}</td></tr>
              </tbody>
            </table>
            <p className="small">Surrogate: {ml?.model.algorithm} on features rain, imperviousness, elevation, drain capacity. Held-out MAE {ml?.model.heldout_mae_cm ?? 0} cm.</p>
          </div>
          <div className="side">
            <h3>Model details</h3>
            <ul className="mlist">
              <li>Algorithm: {ml?.model.algorithm}</li>
              <li>Train / test: {ml?.model.n_train} / {ml?.model.n_test}</li>
              <li>Held-out MAE: {ml?.model.heldout_mae_cm} cm</li>
            </ul>
            <h3>Data provenance</h3>
            {(ml?.provenance ?? []).map((p) => (
              <div key={p.layer} className="prov"><b>{p.layer}</b> — {p.source} <span className="tag">{p.status}</span></div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
