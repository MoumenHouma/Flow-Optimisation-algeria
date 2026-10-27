import { useEffect, useRef, useState } from "react";

import type { LivePosition, Track } from "@/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Public delivery tracking (F18) — no auth; a direct fetch (not apiFetch) so a
// customer without a session isn't bounced to /login.
export async function fetchTrack(token: string): Promise<Track> {
  const res = await fetch(`${BASE_URL}/api/v1/track/${token}`);
  if (!res.ok) throw new Error(String(res.status));
  return (await res.json()) as Track;
}

// Live fleet positions via SSE-over-fetch (F18). EventSource can't send the
// Bearer header, so we stream the response body and parse `data:` frames.
export function useLivePositions(): { positions: LivePosition[]; connected: boolean } {
  const [positions, setPositions] = useState<LivePosition[]>([]);
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    const token = localStorage.getItem("access_token");

    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/v1/tracking/stream`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (!res.ok || !res.body) return;
        setConnected(true);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            const line = frame.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            try {
              setPositions(JSON.parse(line.slice(5).trim()) as LivePosition[]);
            } catch {
              // ignore a malformed frame
            }
          }
        }
      } catch {
        // aborted or network error — connection simply ends
      } finally {
        setConnected(false);
      }
    })();

    return () => controller.abort();
  }, []);

  return { positions, connected };
}
