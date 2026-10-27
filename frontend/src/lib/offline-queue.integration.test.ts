import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/stores/auth-store";

import { enqueueStatus, flushQueue, getCountSnapshot, refreshCount } from "./offline-queue";

// Integration test: real api-client runs (only global fetch is stubbed), so the
// replay path exercises the actual 401 handling + token refresh — the bug a
// mocked api-client hides. Verifies a driver offline past the ~15 min access
// token can still sync on reconnect instead of being bounced to /login.

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(async () => {
  globalThis.indexedDB = new IDBFactory();
  localStorage.clear();
  useAuthStore.getState().setTokens("expired-access", "valid-refresh");
  await refreshCount();
});

describe("offline-queue replay integration", () => {
  it("refreshes an expired access token mid-replay, then retries — no redirect", async () => {
    await enqueueStatus("d1", { status: "delivered" });

    const seen: { url: string; auth: string | null }[] = [];
    let statusCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const headers = new Headers(init?.headers);
        seen.push({ url, auth: headers.get("Authorization") });
        if (url.endsWith("/api/v1/auth/refresh")) {
          return json({ access_token: "fresh-access", refresh_token: "next-refresh", token_type: "bearer" });
        }
        if (url.endsWith("/status")) {
          statusCalls += 1;
          return statusCalls === 1 ? json({ detail: "expired" }, 401) : json({});
        }
        return json({}, 404);
      }),
    );

    const drained = await flushQueue();

    expect(drained).toBe(true);
    expect(getCountSnapshot()).toBe(0);
    // First status attempt (expired) -> refresh -> retry with the fresh token.
    expect(seen.map((s) => s.url.split("/api/v1")[1])).toEqual([
      "/driver/deliveries/d1/status",
      "/auth/refresh",
      "/driver/deliveries/d1/status",
    ]);
    expect(seen[2].auth).toBe("Bearer fresh-access");
    // The replay must NOT bounce the driver to /login: with suppressAuthRedirect
    // the real api-client never calls window.location.assign (jsdom would throw
    // "Not implemented: navigation" if it did, failing this test).
    expect(localStorage.getItem("access_token")).toBe("fresh-access");
  });

  it("keeps the item queued when the refresh token is also invalid", async () => {
    useAuthStore.getState().setTokens("expired-access", "revoked-refresh");
    await enqueueStatus("d2", { status: "delivered" });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/api/v1/auth/refresh")) return json({ detail: "revoked" }, 401);
        return json({ detail: "expired" }, 401); // status endpoint
      }),
    );

    const drained = await flushQueue();

    expect(drained).toBe(false);
    expect(getCountSnapshot()).toBe(1); // still queued, not dropped
  });
});
