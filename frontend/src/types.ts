export type Point = { x: number; y: number };
export type Cell = Point & {
  elev: number; imperv: number; mmh: number; depth_cm: number;
};
export type DrainNode = {
  ix: number; iy: number; x: number; y: number; elev: number;
  capacity_m3min: number; inflow_m3min: number; surcharge_m3min: number;
};
export type DrainEdge = { fr: number; to: number };
export type Route = {
  mode: string; path: Point[]; distance_km: number; max_depth_cm: number;
  flooded_cells_on_path: number; visited_nodes: number; explanations: string[]; error?: string;
};
export type RoutesResp = {
  revision: number; recommended: string; start: Point; goal: Point;
  routes: Route[];
};
export type FloodResp = {
  clock_min: number; cells: Cell[]; summary: {
    flooded_cells: number; of: number; max_depth_cm: number; mean_mmh: number; storm_active: boolean;
  }; disclaimer: string;
};
export type MLResp = {
  model: { trained: boolean; n_train: number; n_test: number; heldout_mae_cm: number; algorithm: string; features: string[]; target: string };
  compare: { ml_mae_cm: number; baseline_mae_cm: number; ml_beats_baseline_pct: number;
    ml: { hit_rate: number; false_alarm_rate: number };
    baseline: { hit_rate: number; false_alarm_rate: number } };
  provenance: { layer: string; source: string; status: string }[];
};
export type DomainT = DomainResp;
export type DomainResp = {
  scenario: { name: string; clock_min: number; storm_active: boolean; revision: number; disclaimer: string; events: { t:number; type:string; message:string }[] };
  grid: { width: number; height: number };
  drain_nodes: number; drain_edges: number; summary: FloodResp["summary"];
};
