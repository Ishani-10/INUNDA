"""INUNDA — Flood-safe route engine.

Given the predicted street-depth field, build a cost surface where deep water
is expensive (or impassable), then run A* over the street grid to produce a
flood-safe alternative route versus the naive shortest path.
"""
from __future__ import annotations

import heapq
from math import hypot
from typing import Any

from . import hydraulics
from . import scenario as sc


def _depth_map(eng) -> dict[tuple[int, int], float]:
    cells = hydraulics.run(eng)["cells"]
    return {(c["x"], c["y"]): c["depth_cm"] for c in cells}


def _astar(eng, start, goal, mode: str) -> dict[str, Any]:
    W, H = sc.W, sc.H
    depth = _depth_map(eng)
    start = tuple(start); goal = tuple(goal)

    def cell_cost(x: int, y: int) -> float:
        d = depth.get((x, y), 0.0)
        if mode == "shortest":
            # shortest ignores floods (except absolute impassable)
            return 1.0 if d < 60 else float("inf")
        # flood-safe: penalise depth; deep water is blocked
        if d >= 35.0:
            return float("inf")
        return 1.0 + (d / 35.0) ** 2 * 8.0

    open_q = [(0.0, 0.0, start)]
    gscore = {start: 0.0}
    came = {}
    dirs = [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
    visited = 0
    while open_q:
        _, g, node = heapq.heappop(open_q)
        if g != gscore.get(node):
            continue
        visited += 1
        if node == goal:
            break
        x, y = node
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= W or ny >= H:
                continue
            move = 1.414 if dx and dy else 1.0
            c = cell_cost(nx, ny)
            if c == float("inf"):
                continue
            ng = g + c * move
            nxt = (nx, ny)
            if ng < gscore.get(nxt, float("inf")):
                came[nxt] = node
                gscore[nxt] = ng
                h = hypot(goal[0] - nx, goal[1] - ny)
                heapq.heappush(open_q, (ng + h, ng, nxt))
    if goal not in came:
        return {"mode": mode, "error": "No flood-safe route found", "path": []}
    path = [goal]
    while path[-1] != start:
        path.append(came[path[-1]])
    path.reverse()
    distance = sum(hypot(path[i][0]-path[i-1][0], path[i][1]-path[i-1][1]) * 8.0
                   for i in range(1, len(path)))
    max_depth = max(depth.get(p, 0.0) for p in path)
    flooded = sum(1 for p in path if depth.get(p, 0.0) > 2.5)
    exps = []
    if mode == "flood-safe":
        exps.append("Routes around predicted deep-water cells")
    if max_depth > 20:
        exps.append("Warning: path passes through elevated forecast depth, operator check advised")
    return {"mode": mode, "path": [{"x": x, "y": y} for x, y in path],
            "distance_km": round(distance, 1),
            "max_depth_cm": round(max_depth, 1),
            "flooded_cells_on_path": flooded,
            "visited_nodes": visited, "explanations": exps}


def plan_all(eng) -> dict[str, Any]:
    W, H = sc.W, sc.H
    start = (6, 30); goal = (W - 7, 5)
    out = {"revision": eng.revision, "recommended": "flood-safe",
           "start": {"x": start[0], "y": start[1]},
           "goal": {"x": goal[0], "y": goal[1]}, "routes": []}
    for mode in ("flood-safe", "shortest"):
        try:
            out["routes"].append(_astar(eng, start, goal, mode))
        except Exception as exc:
            out["routes"].append({"mode": mode, "error": str(exc), "path": []})
    return out
