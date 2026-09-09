# INUNDA — Urban Flood Nowcasting System (Drainage + Rainfall Coupling)

**SIH 2026 Problem Statement:** 26085 · Ministry of Earth Sciences (MoES) / NCMRWF · Software · Disaster Management
**Team:** Lord VoldyCoder

INUNDA predicts **street-level flood depth (cm)** 0–3 hours ahead by **coupling** rainfall nowcast, terrain, and a graph model of the underground storm-drain network. This is the *coupled* approach the problem statement explicitly demands — not an isolated weather model.

> **Honest scope:** This is a working **illustrative MVP**. The rain, terrain and drain network are **generated deterministic data** (clearly labelled everywhere) so the demo runs offline and is reproducible. The **ML model is real and trained**, and it demonstrably **beats a naive rainfall-threshold baseline**. Real-city data (IMERG radar, SRTM DEM, municipal drain GIS) plugs in via the same engine seams.

---

## Quick start

### Prerequisites
- Python 3.12+
- Node 18+ / npm
- (Optional) Docker

### 1. Backend
```bash
cd backend
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q        # 5 tests
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
API docs: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run build
npm run dev
```
Open: http://localhost:5173/

> The frontend dev server proxies `/api` to `http://127.0.0.1:8000`.

### 3. Run everything from scratch
```bash
bash scripts/run_demo.sh
```

---

## What it does (the three views)
| View | What you see |
|---|---|
| **Nowcast** | Live flood-depth map (coupled rain→terrain→drain), rain vs depth toggle, lead-time slider, stats. |
| **Flood-Safe Routes** | Green = flood-safe route around the flooded basin; red = shortest route that cuts through it. |
| **ML Model** | The trained depth surrogate vs the naive rainfall-threshold baseline, + metadata & provenance. |

### Core actions
- **Advance 30m** — move the nowcast window forward.
- **Toggle Rain** — turn the storm cell on/off and watch the flood map respond.
- **Reset** — back to T+0.
- **Lead time slider** — sweep the 0–3 h nowcast horizon.

---

## Architecture
```
Rain nowcast ──► Surface runoff (rain × imperviousness) ──► nearest drain node
                                                                    │
                                     Drain graph (capacity-limited) │
                                                                    ▼
                          surcharge = inflow − capacity  ──► street depth (cm)
                                                                    │
                 GIS dashboard ◄── depth field ＋ flood-safe route (A*)
```

### Backend (`backend/app/`)
- `engine/scenario.py` — deterministic urban domain: 48×36 grid, DEM basin, imperviousness field, 130 drain nodes, 237 directed gravity edges, advecting rain cell.
- `engine/hydraulics.py` — the **coupled** model: rain×impervious → runoff → drain inflow → capacity-limited outflow → surcharge → street depth in cm.
- `engine/ml_engine.py` — **trained Gradient-Boosted** depth surrogate + the naive threshold baseline, with honest hit-rate / false-alarm / MAE comparison.
- `engine/routing.py` — A* on a depth cost surface → flood-safe vs shortest route.
- `main.py` — FastAPI endpoints.

### Frontend (`frontend/src/`)
- `App.tsx` — 3 views + actions. `components/FloodMap.tsx` — SVG grid renderer. `api.ts`, `types.ts`, `styles.css`.

---

## API reference
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness + ML trained flag |
| GET | `/api/domain` | Scenarios, grid, drain summary |
| GET | `/api/rain` | Current nowcast rain field |
| GET | `/api/flood?horizon_min=` | Predicted street depth at a lead |
| GET | `/api/routes` | Flood-safe + shortest routes |
| GET | `/api/ml` | ML model + baseline comparison + provenance |
| POST | `/api/scenario/advance` | `{minutes}` — advance nowcast |
| POST | `/api/scenario/toggle-storm` | Toggle rain on/off |
| POST | `/api/scenario/reset` | Reset |

---

## Validation (the baseline-first promise)
The ML surrogate is trained on the mechanistic model's output across storm stages and evaluated on a **held-out split**:

| | Hit rate | False-alarm | MAE (cm) |
|---|---|---|---|
| **Our ML** | **0.892** | 0.144 | **1.50** |
| Naive threshold baseline | 0.079 | 0 | 5.66 |

**Result: the ML is ~73.5% better in MAE and dramatically better at detecting floods** than simply saying "rain above X = flood." Held-out MAE: **1.84 cm**.

---

## Honesty / provenance
Every environmental field is labelled `illustrative` (generated demo data). The system is a **decision-support prototype** — it recommends; operators approve; it does **not** autonomously evacuate or control infrastructure.

## Roadmap
1. Real radar/IMERG rain + SRTM DEM + municipal drain GIS (real-data adapters).
2. Historical storm validation vs observed flood points.
3. MapLibre GL real city tiles.
4. Confidence-gated operator alerting.

See `docs/` for the design and `POLARIS_Technical_Document.md` / `INUNDA_Technical_Document.md` for full specs (INUNDA doc now reflects this built prototype).
