import type { DomainT, FloodResp, RoutesResp, MLResp } from "./types";

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string; service: string; revision: number; ml_trained: boolean }>("/api/health"),
  domain: () => get<DomainT>("/api/domain"),
  flood: (horizon = 0) => get<FloodResp>(`/api/flood?horizon_min=${horizon}`),
  routes: () => get<RoutesResp>("/api/routes"),
  ml: () => get<MLResp>("/api/ml"),
  advance: (minutes = 30) => post<{ state: unknown; routes: RoutesResp }>("/api/scenario/advance", { minutes }),
  toggle: () => post<{ state: unknown; routes: RoutesResp }>("/api/scenario/toggle-storm"),
  reset: () => post<{ state: unknown; routes: RoutesResp }>("/api/scenario/reset"),
};
