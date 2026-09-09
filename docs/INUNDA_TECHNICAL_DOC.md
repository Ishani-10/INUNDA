# INUNDA — Technical Documentation (v1 · built prototype)

**Project:** INUNDA — Urban Flood Nowcasting System (Drainage + Rainfall Coupling)
**SIH 2026 PS:** 26085 · MoES / NCMRWF · Software · Disaster Management
**Status:** This document now reflects the **built, tested, running prototype** (not a design-only spec). Every section maps to real code in `backend/` and `frontend/`.

---

## 1. Executive Summary
INUNDA predicts **street-level flood depth (cm)** 0–3 hours ahead by coupling three things the problem statement mandates: **rainfall nowcast** × **terrain/imperviousness** × **a directed graph of the storm-drain network**. It is the *coupled* framework the PS asks for — rain is routed across terrain, pushed through a capacity-limited drain graph, and drain **surcharge/backflow** is translated into **street water depth**.

**Key differentiators implemented**
1. **Coupled, not isolated-weather** — rain→surface→drain→depth in one pipleine.
2. **Graph-based hydraulics** — 130 drain nodes, 237 directed gravity edges, per-node capacity.
3. **0–3 h nowcast** with a lead-time slider.
4. **Depth in cm per street cell** (not a binary flood flag).
5. **Flood-safe route** computed by A* over a depth cost surface (vs the naive shortest path).
6. **Real, trained ML** depth surrogate that **beats a naive rainfall-threshold baseline**.
7. **Baseline-first + provenance** throughout.

---

## 2. Architecture (implemented)
```
rain (advecting storm cell)  ──►  runoff = rain × imperviousness
                                        │  (assigned to nearest drain node)
                                        ▼
                            drain node inflow  ──►  capacity-limited outflow
                                        │
                         surcharge = max(0, inflow − capacity)
                                        │
                     street depth (cm) per cell (modulated by local relief)
                                        │
         ┌──────────────────────────────┴──────────────────────────────┐
         ▼                                                             ▼
   GIS depth field (Nowcast view)                A* flood-safe route (Routes view)
```

---

## 3. Technology stack & why
| Layer | Tech | Why |
|---|---|---|
| Backend | **Python 3.12 + FastAPI + Uvicorn + Pydantic** | Typed async API, auto OpenAPI docs, native validation. |
| Numerical | **numpy** | Array math for fields. |
| ML | **scikit-learn (GradientBoostingRegressor)** | Fast, robust regressor; easy baseline comparison. |
| Graph/routing | **heapq A\*** (pure Python) | Flood-safe pathfinding on a depth cost surface. |
| Frontend | **React + TypeScript + Vite** | Reusable components, executable type contracts, fast HMR/build. |
| Validation | **pytest + FastAPI TestClient** | Regression + API-level tests. |

Shared architecture spine reused from POLARIS (FastAPI + React/Vite) so the team runs one pattern across both projects.

---

## 4. Domain model (`engine/scenario.py`)
- **Grid:** `W=48, H=36` street cells → **1,728 cells**.
- **DEM `elev(x,y)`:** 6–11 m with a **low-lying basin** around cell `(24,20)` — water pools there.
- **Imperviousness `impervious(x,y)`:** 0.05–0.97, denser concrete toward the city core.
- **Drain network:** `NODES_X=13, NODES_Y=10` → **130 nodes** every 4 cells; **directed gravity edges** (237) connect higher→lower nodes. Each node has `capacity_m3min` from elevation (lower = better outfall).
- **Rain `rain_mmh(x,y)`:** a gaussian storm cell advected eastward, `peak=72 mm/h`, decaying with distance; `storm_active` toggles it.
- **State machine:** `advance(minutes)`, `toggle_storm()`, `reset()` all bump `revision` + append audit events. Disclaimer is always present.

## 5. Coupled hydraulics (`engine/hydraulics.py`) — the core
1. **Runoff per cell:** `runoff = rain × impervious` (concrete sheds, green infiltrates); assigned to nearest node every 4 cells.
2. **Node inflow:** sum of runoff of cells mapped to the node.
3. **Capacity limit:** `outflow = min(inflow, cap)`; `surcharge = max(0, inflow − cap)`.
4. **Surcharge → depth:** sustained surcharge accumulates as standing water over the node's catchment (scale factor `0.11` cm per mm/h, ~45 min window).
5. **Relief modulation:** cells lower than their node pool deeper; light ponding in the basin.
Result: per-cell `depth_cm` clamped 0–120, plus a `summary` (flooded cells, max depth, mean rain).

## 6. ML depth surrogate (`engine/ml_engine.py`)
- **Model:** `GradientBoostingRegressor(n_estimators=220, max_depth=4)` predicting `depth_cm`.
- **Features:** `[rain_mmh, imperviousness, elevation_m, drain_capacity_m3min]`.
- **Training data:** sweep of storm stages (0/30/60/90/120/150/180 min) from the mechanistic model → ~12,096 samples, 80/20 split.
- **Baseline:** naive rule `depth = 0.22*(rain − 30) if rain > 30 else 0`.
- **Results (held-out):**
  | | Hit rate | False-alarm | MAE (cm) |
  |---|---|---|---|
  | **Our ML** | **0.892** | 0.144 | **1.50** |
  | baseline | 0.079 | 0 | 5.66 |
  → **~73.5% lower MAE** and far better detection. Held-out MAE **1.84 cm**.

## 7. Flood-safe routing (`engine/routing.py`)
- Build a **depth cost surface** from the predicted field.
- **Flood-safe** mode: cells ≥35 cm are impassable; deeper water costs `1 + (d/35)²·8`.
- **Shortest** mode: ignores flood (except ≥60 cm) — a comparison route.
- **A\*** over the 48×36 grid (8-directional, Euclidean heuristic). Both routes start `(6,30)` → goal `(41,5)`.
- Returns `distance_km`, `max_depth_cm`, `flooded_cells_on_path`, `explanations[]`.

## 8. API (`main.py`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + ml_trained |
| GET | `/api/domain` | scenario + grid + drain summary |
| GET | `/api/rain` | nowcast rain field |
| GET | `/api/flood?horizon_min=` | predicted street depth at a lead |
| GET | `/api/routes` | flood-safe + shortest |
| GET | `/api/ml` | model + baseline + provenance |
| POST | `/api/scenario/advance` | `{minutes}` advance |
| POST | `/api/scenario/toggle-storm` | rain on/off |
| POST | `/api/scenario/reset` | reset |
At import time the ML model is trained once (`if not _model.trained: _model.train()`).

## 9. Frontend (`frontend/src/`)
- `App.tsx` — 3 tabs (Nowcast / Flood-Safe Routes / ML Model) + action bar (Advance, Toggle Rain, Reset, lead slider, depth/rain toggle) + status bar (clock, storm state, flooded count, max depth, last event).
- `components/FloodMap.tsx` — SVG grid renderer (48×36 cells), route polylines (green/red), drain-node dots.
- `components/Header.tsx`, `api.ts`, `types.ts`, `styles.css`.
- Vite dev server proxies `/api` → `http://127.0.0.1:8000`.

## 10. Data model (types)
```ts
type Cell = { x;y; elev; imperv; mmh; depth_cm };
type Route = { mode; path:Point[]; distance_km; max_depth_cm; flooded_cells_on_path;
               visited_nodes; explanations[]; error? };
type MLResp = { model:{trained;n_train;n_test;heldout_mae_cm;algorithm;features;target};
                compare:{ ml_mae_cm; baseline_mae_cm; ml_beats_baseline_pct;
                          ml:{hit_rate;false_alarm_rate}; baseline:{hit_rate;false_alarm_rate} };
                provenance:{layer;source;status}[] };
```

## 11. Testing
- `backend/tests/test_engine.py` (5 tests, all pass): domain shape, storm toggle affects depth, advance changes revision, nodes/edges present, depth in bounds.
- Frontend builds with `tsc -b && vite build` (TypeScript gate). Playwright smoke test confirmed **0 console errors** across all three views.

## 12. Error handling, safety, ethics
- Routes that cannot be found return `{error}` not a crash.
- **Confidence-gated / human-in-the-loop:** the platform *recommends*; operators approve.
- **Provenance** labels every generated layer `illustrative`; disclaimer always shown.
- Not an autonomous evacuation/control system.

## 13. Known limitations (honest)
- Rain, DEM and drain graph are **generated** (illustrative) — real-city adapters needed for operational use.
- Surcharge→depth is a simplified scale model (not a full SWMM solution).
- Single deterministic storm; no multi-year historical validation yet.

## 14. Roadmap
1. Real IMERG/radar rain + SRTM DEM + municipal drain GIS (adapters).
2. Historical storm validation vs observed flood points (chronological split).
3. MapLibre GL real city tiles.
4. Confidence-gated operator alerting.

## 15. References
- SIH 26085 (MoES/NCMRWF) — coupled rain+DEM+drainage, 0–3 h, street depth, GIS dashboard, safer-route API.
- GPM/IMERG precipitation, SRTM/Cartosat DEM, OpenStreetMap + municipal storm-water GIS.
- Manning-equation open-channel hydraulics; raster flow-accumulation methods.
- POLARIS technical doc — shared architecture spine & A* routing pattern.
