"""INUNDA — Scenario/domain engine.

Builds a small, deterministic, self-consistent urban domain:
  - a W x H grid of "street cells",
  - a terrain (DEM) field with a low-lying basin,
  - an imperviousness (concrete) field,
  - a grid of drain nodes (manholes) and a directed drain graph,
  - a rainfall nowcast field that advects a storm cell over time.

Everything is deterministic so the demo is reproducible and offline-capable.
It is intentionally labelled as illustrative generated data (no real city data).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

W, H = 48, 36          # grid of "street cells"
NODE_STEP = 4          # one drain node every NODE_STEP cells
NODES_X = W // NODE_STEP + 1
NODES_Y = H // NODE_STEP + 1


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def node_xy(ix: int, iy: int) -> tuple[int, int]:
    return (ix * NODE_STEP, iy * NODE_STEP)


@dataclass
class ScenarioEngine:
    scenario_id: str = "demo-metro"
    clock_min: int = 0                 # minutes since nowcast window start (0-180)
    storm_active: bool = True
    review_events: list[dict[str, Any]] = field(default_factory=list)
    revision: int = 1

    def __post_init__(self) -> None:
        if not self.review_events:
            self.review_events = [{"t": 0, "type": "SYSTEM_READY", "message": "INUNDA domain loaded"}]

    # ---- static domain fields -------------------------------------------
    def elev(self, x: int, y: int) -> float:
        """DEM (metres). A low-lying basin around a centre -> water pools there."""
        dx = (x - 24) / 12.0
        dy = (y - 20) / 9.0
        basin = 14.0 * max(0.0, 1.0 - math.sqrt(dx * dx + dy * dy))
        noise = 1.2 * math.sin(x / 2.3) + 0.9 * math.cos(y / 1.9)
        return 6.0 + 5.0 * (y / H) - basin + noise

    def impervious(self, x: int, y: int) -> float:
        """Fraction of concrete (0-1). Denser toward the city centre."""
        dx = (x - 24) / 16.0
        dy = (y - 18) / 12.0
        core = 0.92 * math.exp(-(dx * dx + dy * dy) * 1.1)
        return clamp(0.30 + core, 0.05, 0.97)

    # ---- drain graph ------------------------------------------------------
    def nodes(self) -> list[dict[str, Any]]:
        """Drain nodes every NODE_STEP cells. Each has a capacity (m3/min)."""
        out = []
        for iy in range(NODES_Y):
            for ix in range(NODES_X):
                cx, cy = node_xy(ix, iy)
                # lower elevation -> larger capacity (better outfall); centre lower
                cap = 3.6 + (18.0 - self.elev(cx, cy)) * 0.4
                out.append({
                    "ix": ix, "iy": iy, "x": cx, "y": cy,
                    "elev": round(self.elev(cx, cy), 2),
                    "capacity_m3min": round(cap, 2),
                    "inflow_m3min": 0.0,
                    "surcharge_m3min": 0.0,
                })
        return out

    def node_index(self, ix: int, iy: int) -> int:
        return iy * NODES_X + ix

    def graph(self) -> dict[str, Any]:
        """Directed edges from higher to lower nodes (gravity flow)."""
        n = self.nodes()
        edges = []
        for iy in range(NODES_Y):
            for ix in range(NODES_X):
                i = self.node_index(ix, iy)
                for dx, dy in ((1, 0), (0, 1)):
                    nx_, ny_ = ix + dx, iy + dy
                    if nx_ >= NODES_X or ny_ >= NODES_Y:
                        continue
                    j = self.node_index(nx_, ny_)
                    # gravity: flow from higher elevation node to lower
                    if n[i]["elev"] > n[j]["elev"] + 0.15:
                        edges.append({"fr": i, "to": j})
                    elif n[j]["elev"] > n[i]["elev"] + 0.15:
                        edges.append({"fr": j, "to": i})
                    else:
                        edges.append({"fr": i, "to": j})  # tie -> east/south
        return {"nodes": n, "edges": edges, "nodes_x": NODES_X, "nodes_y": NODES_Y}

    # ---- rainfall nowcast ---------------------------------------------------
    def rain_mmh(self, x: int, y: int) -> float:
        """Rain intensity (mm/h) by advecting a gaussian storm cell eastward."""
        t = self.clock_min / 60.0
        cx = 8.0 + t * 6.0
        cy = 20.0 - 2.0 * math.sin(t / 1.2)
        d = math.hypot(x - cx, y - cy)
        peak = 72.0 if self.storm_active else 0.0
        base = 4.0 if self.storm_active else 0.0
        return clamp(base + peak * math.exp(-(d * d) / 34.0), 0.0, 130.0)

    def rain_field(self) -> list[dict[str, Any]]:
        return [{"x": x, "y": y, "mmh": round(self.rain_mmh(x, y), 1)}
                for y in range(H) for x in range(W)]

    # ---- scenario actions ---------------------------------------------------
    def state(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": "Illustrative Metro Flood Nowcast Demo",
            "clock_min": self.clock_min,
            "storm_active": self.storm_active,
            "revision": self.revision,
            "grid": {"width": W, "height": H, "cells": W * H},
            "window_hours": 3,
            "events": self.review_events[-12:],
            "disclaimer": "Illustrative generated urban scenario — not operational flood data",
        }

    def advance(self, minutes: int = 30) -> dict[str, Any]:
        self.clock_min = min(180, self.clock_min + minutes)
        self.revision += 1
        self.review_events.append({"t": self.clock_min, "type": "NOWCAST_ADVANCED",
                                   "message": f"Nowcast advanced to T+{self.clock_min // 60}h{self.clock_min % 60:02d}m"})
        return self.state()

    def toggle_storm(self) -> dict[str, Any]:
        self.storm_active = not self.storm_active
        self.revision += 1
        self.review_events.append({"t": self.clock_min, "type": "STORM_TOGGLE",
                                   "message": "Rainfall source " + ("ON" if self.storm_active else "OFF")})
        return self.state()

    def reset(self) -> dict[str, Any]:
        self.clock_min = 0
        self.storm_active = True
        self.revision += 1
        self.review_events = [{"t": 0, "type": "SYSTEM_RESET", "message": "Scenario reset to T+0h00m"}]
        return self.state()
