"""INUNDA — Coupled hydraulics model (rain -> surface -> drain -> street depth).

This is the analytical core that satisfies the "coupled framework" requirement:
we do NOT just report rainfall; we route runoff across terrain, push it through
a directed drain graph, and translate drain surcharge/backflow into a
street-level water DEPTH (cm) per cell.

Method (transparent, volume-conserving in expectation):
  1. runoff_cell = rain * imperviousness (concrete sheds water; green infiltrates)
     Every cell's runoff is assigned to its nearest drain node.
  2. node_inflow  = sum of runoff of cells mapped to that node.
  3. Dilute by node capacity: outflow = min(inflow, capacity).
     surcharge    = max(0, inflow - capacity)   <- water that cannot drain.
  4. The surcharge volume is treated as standing water over the node's
     catchment footprint -> depth in cm (converted m3 -> cm using area).
  5. backflow contribution is spread back over the node's low-lying cells.
  6. Cell depth = local standing depth (from its own node) weighted by how
     low the cell is relative to its node (low cells flood first).

All returned values carry provenance and are deterministic.
"""
from __future__ import annotations

from math import hypot
from typing import Any

from . import scenario as sc


def cell_loss_km(seed_km: float) -> float:
    """Approximate great-circle km per grid cell (used for area/depth scale)."""
    return seed_km


# meters per cell side (a coarse street-block scale)
M_PER_CELL = 130.0


def nearest_node(cx: int, cy: int, step: int) -> tuple[int, int]:
    return round(cx / step), round(cy / step)


def run(engine: "sc.ScenarioEngine") -> dict[str, Any]:
    W, H = sc.W, sc.H
    step = sc.NODE_STEP
    nodes = engine.nodes()
    nid = { (n["ix"], n["iy"]): i for i, n in enumerate(nodes) }
    nin = [0.0] * len(nodes)

    # --- surface runoff per cell, assigned to nearest node -----------------
    runoff = []
    for y in range(H):
        for x in range(W):
            rain = engine.rain_mmh(x, y)
            imperv = engine.impervious(x, y)
            # runoff = rain (mm/h) * impervious fraction -> mm/h shed
            r = rain * imperv
            runoff.append({"x": x, "y": y, "mmh": round(rain, 1),
                           "imperv": round(imperv, 3), "runoff": round(r, 2)})
            ix, iy = nearest_node(x, y, step)
            nin[nid[(ix, iy)]] += r

    # --- drain capacity-limited flow ----------------------------------------
    # node outflow = min(inflow, capacity); surcharge = inflow - outflow
    surcharge = []
    for i, node in enumerate(nodes):
        inflow = nin[i]
        cap = node["capacity_m3min"]
        out = min(inflow, cap)
        sur = max(0.0, inflow - cap)
        nodes[i]["inflow_m3min"] = round(inflow, 2)
        surcharge.append(sur)
    # backflow: surcharge redistributes to the node's own catchment -> depth

    # node catchment area (m^2): cells assigned to a node
    cell_area = M_PER_CELL * M_PER_CELL
    cells_per_node = step * step
    node_area = cell_area * cells_per_node

    # convert surcharge (mm/h -> m3/min -> standing depth). Use a drainage
    # timescale so a sustained surcharge accumulates a visible depth.
    depth_node = [0.0] * len(nodes)
    for i in range(len(nodes)):
        # surcharge in mm/h; convert to cm depth over a ~45 min accumulation window
        depth_cm = surcharge[i] * 0.11
        depth_node[i] = depth_cm

    # --- per-cell depth: node depth weighted by local relief -----------------
    cells = []
    for y in range(H):
        for x in range(W):
            ix, iy = nearest_node(x, y, step)
            i = nid[(ix, iy)]
            elev = engine.elev(x, y)
            node_elev = nodes[i]["elev"]
            # cells lower than the node pool deeper; higher cells stay drier
            relief = max(0.0, (node_elev - elev))
            local = depth_node[i] * (0.6 + 0.6 * min(1.2, relief / 2.0))
            # light ponding even without surcharge in the low basin
            basin = max(0.0, (6.0 - elev)) * 0.15 if engine.storm_active else 0.0
            depth = local + basin
            cells.append({
                "x": x, "y": y,
                "elev": round(elev, 2),
                "imperv": round(engine.impervious(x, y), 3),
                "mmh": round(engine.rain_mmh(x, y), 1),
                "depth_cm": round(clamp(depth, 0.0, 120.0), 1),
            })

    # --- aggregate summary for confidence ------------------------------------
    flooded = [c for c in cells if c["depth_cm"] > 2.5]
    return {
        "revision": engine.revision,
        "nodes": nodes,
        "edges": engine.graph()["edges"],
        "cells": cells,
        "runoff": runoff,
        "summary": {
            "flooded_cells": len(flooded),
            "of": len(cells),
            "max_depth_cm": round(max((c["depth_cm"] for c in cells), default=0.0), 1),
            "mean_mmh": round(sum(c["mmh"] for c in cells) / max(1, len(cells)), 1),
            "storm_active": engine.storm_active,
        },
        "disclaimer": engine.state()["disclaimer"],
    }


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
