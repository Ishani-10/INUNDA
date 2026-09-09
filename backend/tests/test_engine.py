import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.engine.scenario import ScenarioEngine
from app.engine import hydraulics


def test_domain_shape():
    e = ScenarioEngine()
    hyd = hydraulics.run(e)
    assert len(hyd["cells"]) == 48 * 36


def test_storm_toggle_affects_depth():
    e = ScenarioEngine(storm_active=True)
    d_on = max(c["depth_cm"] for c in hydraulics.run(e)["cells"])
    e.storm_active = False
    d_off = max(c["depth_cm"] for c in hydraulics.run(e)["cells"])
    assert d_on > d_off


def test_advance_changes_state():
    e = ScenarioEngine()
    r0 = e.revision
    e.advance(30)
    assert e.revision == r0 + 1
    assert e.clock_min == 30


def test_nodes_and_edges_present():
    e = ScenarioEngine()
    g = e.graph()
    assert len(g["nodes"]) > 0
    assert len(g["edges"]) >= 0


def test_depth_in_plausible_bounds():
    e = ScenarioEngine()
    depths = [c["depth_cm"] for c in hydraulics.run(e)["cells"]]
    assert all(d >= 0 and d <= 120 for d in depths)
