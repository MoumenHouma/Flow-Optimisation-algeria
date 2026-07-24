import "fake-indexeddb/auto";
import { Blob as NodeBlob } from "node:buffer";
import { IDBFactory } from "fake-indexeddb";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// jsdom's Blob lacks .arrayBuffer(); Node's implements it (as real browsers do).
const blob = (parts: string[]) => new NodeBlob(parts) as unknown as Blob;

import { ApiError, apiFetch, apiUpload } from "@/lib/api-client";

import { enqueueProof, enqueueStatus, flushQueue, getCountSnapshot, refreshCount } from "./offline-queue";

vi.mock("@/lib/api-client", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: vi.fn(), apiUpload: vi.fn() };
});

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: {
    getState: () => ({ refreshToken: "refresh-tok", setTokens: vi.fn() }),
  },
}));

const mockFetch = vi.mocked(apiFetch);
const mockUpload = vi.mocked(apiUpload);

beforeEach(async () => {
  // Fresh in-memory IndexedDB per test.
  globalThis.indexedDB = new IDBFactory();
  vi.clearAllMocks();
  mockFetch.mockResolvedValue(undefined as never);
  mockUpload.mockResolvedValue(undefined as never);
  await refreshCount();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("offline-queue", () => {
  it("enqueues a status update and drains it on flush", async () => {
    await enqueueStatus("d1", { status: "delivered" });
    expect(getCountSnapshot()).toBe(1);

    const drained = await flushQueue();

    expect(drained).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/driver/deliveries/d1/status",
      expect.objectContaining({ method: "PUT" }),
      expect.objectContaining({ suppressAuthRedirect: true }),
    );
    expect(getCountSnapshot()).toBe(0);
  });

  it("replays in FIFO order — proof before its status", async () => {
    await enqueueProof({ deliveryId: "d2", photo: blob(["x"]) });
    await enqueueStatus("d2", { status: "delivered" });
    expect(getCountSnapshot()).toBe(2);

    const calls: string[] = [];
    mockUpload.mockImplementation(async () => void calls.push("proof") as never);
    mockFetch.mockImplementation(async () => void calls.push("status") as never);

    await flushQueue();

    expect(calls).toEqual(["proof", "status"]);
    expect(getCountSnapshot()).toBe(0);
  });

  it("keeps the item queued on a network failure, then retries", async () => {
    await enqueueStatus("d3", { status: "failed", reason: "absent" });

    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const first = await flushQueue();
    expect(first).toBe(false);
    expect(getCountSnapshot()).toBe(1);

    mockFetch.mockResolvedValueOnce(undefined as never);
    const second = await flushQueue();
    expect(second).toBe(true);
    expect(getCountSnapshot()).toBe(0);
  });

  it("moves a permanently rejected (4xx) item to the dead store", async () => {
    await enqueueStatus("d4", { status: "delivered" });
    await enqueueStatus("d5", { status: "delivered" });

    // First item 422s (dead-letter), second succeeds — queue must not wedge.
    mockFetch.mockRejectedValueOnce(new ApiError(422, "bad"));
    const drained = await flushQueue();

    expect(drained).toBe(true);
    expect(getCountSnapshot()).toBe(0);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("preserves Blob payloads across the IndexedDB round-trip", async () => {
    await enqueueProof({ deliveryId: "d6", photo: blob(["photo-bytes"]), lat: 36.75, lon: 3.06 });

    let sentForm: FormData | undefined;
    mockUpload.mockImplementation(async (_path, form) => {
      sentForm = form as FormData;
      return undefined as never;
    });
    await flushQueue();

    expect(sentForm?.get("photo")).toBeInstanceOf(Blob);
    expect(sentForm?.get("lat")).toBe("36.75");
  });
});
