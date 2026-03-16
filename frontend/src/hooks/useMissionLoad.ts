import { useEffect, useState } from "react";
import { useMissionStore } from "../store";
import type { EvidenceRecord, MissionRecord } from "../types/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function useMissionLoad(): {
  missionId: string | null;
  loading: boolean;
  error: string | null;
} {
  const missionIdFromUrl =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("mission")
      : null;

  const [loading, setLoading] = useState(!!missionIdFromUrl);
  const [error, setError] = useState<string | null>(null);

  const { setMission, setEvidenceList } = useMissionStore();

  useEffect(() => {
    if (!missionIdFromUrl) {
      setLoading(false);
      setMission(null);
      setEvidenceList([]);
      return;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [missionRes, evidenceRes] = await Promise.all([
          fetch(`${API_URL}/missions/${missionIdFromUrl}`),
          fetch(`${API_URL}/missions/${missionIdFromUrl}/evidence`),
        ]);

        if (cancelled) return;

        if (!missionRes.ok) {
          if (missionRes.status === 404) {
            setError("Mission not found.");
          } else {
            setError(`Failed to load mission (${missionRes.status}).`);
          }
          setMission(null);
          setEvidenceList([]);
          setLoading(false);
          return;
        }

        const mission = (await missionRes.json()) as MissionRecord;
        setMission(mission);

        if (!evidenceRes.ok) {
          setEvidenceList([]);
        } else {
          const evidence = (await evidenceRes.json()) as EvidenceRecord[];
          setEvidenceList(evidence);
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Failed to load mission and evidence."
          );
          setMission(null);
          setEvidenceList([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [missionIdFromUrl, setMission, setEvidenceList]);

  return {
    missionId: missionIdFromUrl,
    loading,
    error,
  };
}
