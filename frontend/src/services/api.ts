const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_KEY = "changeme";

export interface MissionResponse {
  id: string;
  objective: string;
  status: string;
  task_graph: unknown[];
  created_at: string;
  updated_at: string;
  briefing: string | null;
}

export async function createMission(objective: string): Promise<MissionResponse> {
  const resp = await fetch(`${API_URL}/missions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ objective }),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`Failed to create mission: ${text}`);
  }
  return resp.json();
}

export async function getMission(id: string): Promise<MissionResponse> {
  const resp = await fetch(`${API_URL}/missions/${id}`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`Failed to get mission: ${text}`);
  }
  return resp.json();
}

export async function synthesizeMission(id: string): Promise<MissionResponse> {
  const resp = await fetch(`${API_URL}/missions/${id}/synthesize`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new Error(`Failed to synthesize: ${text}`);
  }
  return resp.json();
}
