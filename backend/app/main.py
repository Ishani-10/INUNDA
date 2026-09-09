"""INUNDA — FastAPI decision-support backend.

Provides the coupled urban-flood nowcast model, the ML depth surrogate, the
flood-safe route engine, and honest metrics. Intended as an illustrative SIH
MVP, not an operational flood-warning system.
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine.scenario import ScenarioEngine
from .engine import hydraulics
from .engine.ml_engine import _model, metrics
from .engine.routing import plan_all

app = FastAPI(
    title="INUNDA Urban Flood Nowcast API",
    version="0.1.0",
    description="Coupled rain+DEM+drainage flood nowcast — illustrative SIH MVP, not operational",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

engine = ScenarioEngine()


class AdvanceRequest(BaseModel):
    minutes: int = Field(default=30, ge=10, le=60)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "inunda-api", "revision": engine.revision,
            "ml_trained": _model.trained}


@app.get("/api/domain")
def domain():
    g = engine.graph()
    sm = hydraulics.run(engine)["summary"]
    return {"scenario": engine.state(), "grid": {"width": 48, "height": 36},
            "drain_nodes": len(g["nodes"]), "drain_edges": len(g["edges"]),
            "summary": sm}


@app.get("/api/rain")
def rain():
    return {"clock_min": engine.clock_min, "window_hours": 3,
            "field": engine.rain_field(), "disclaimer": engine.state()["disclaimer"]}


@app.get("/api/flood")
def flood(horizon_min: int = Query(default=0, ge=0, le=180)):
    # simulate a future nowcast by advancing a temporary engine copy
    tmp = ScenarioEngine(clock_min=min(180, engine.clock_min + horizon_min),
                         storm_active=engine.storm_active)
    hyd = hydraulics.run(tmp)
    return {"clock_min": tmp.clock_min, "cells": hyd["cells"], "summary": hyd["summary"],
            "disclaimer": hyd["disclaimer"]}


@app.get("/api/routes")
def routes():
    return plan_all(engine)


@app.get("/api/ml")
def ml_result():
    return metrics(engine)


@app.post("/api/scenario/advance")
def advance(req: AdvanceRequest):
    return {"state": engine.advance(req.minutes), "routes": plan_all(engine)}


@app.post("/api/scenario/toggle-storm")
def toggle():
    return {"state": engine.toggle_storm(), "routes": plan_all(engine)}


@app.post("/api/scenario/reset")
def reset():
    return {"state": engine.reset(), "routes": plan_all(engine)}


if not _model.trained:
    _model.train()
