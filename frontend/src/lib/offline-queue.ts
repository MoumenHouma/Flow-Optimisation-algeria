// Offline mutation queue for the Driver PWA (Phase D).
//
// Drivers lose signal mid-route (dead zones, basements, rural stops). Status
// updates and proof-of-delivery uploads are captured here in IndexedDB when the
// network is unavailable and replayed, in order, on reconnect. Location pings
// are deliberately NOT queued — a stale GPS fix is worthless.
//
// Replay runs in the app context (not a service worker) so it can refresh an
// expired access token and drive UI feedback. Items are removed only on a 2xx,
// so a replayed "delivered" is safe (the backend tolerates it); a non-401 4xx
// moves the item to a dead store rather than wedging the queue.
import { ApiError, apiFetch, apiUpload } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

const DB_NAME = "routeopt-offline";
const DB_VERSION = 1;
const STORE = "mutations";
const DEAD = "dead";

export interface StatusBody {
  status: "en_route" | "delivered" | "failed";
  reason?: string;
  lat?: number;
  lon?: number;
  cod_collected?: number;
  cod_method?: "cash" | "baridimob" | "ccp" | "none";
}

interface StatusItem {
  seq?: number;
  kind: "status";
  deliveryId: string;
  body: StatusBody;
  createdAt: number;
  attempts: number;
}

interface ProofItem {
  seq?: number;
  kind: "proof";
  deliveryId: string;
  // Stored as ArrayBuffer (+ MIME type) rather than Blob: buffers are reliably
  // structured-cloneable everywhere, whereas Blob-in-IndexedDB support varies.
  photoBuf?: ArrayBuffer;
  photoType?: string;
  sigBuf?: ArrayBuffer;
  sigType?: string;
  lat?: number;
  lon?: number;
  createdAt: number;
  attempts: number;
}

export type QueueItem = StatusItem | ProofItem;

// --- IndexedDB plumbing (thin promisified wrapper, no extra dependency) -------

function hasIndexedDB(): boolean {
  return typeof indexedDB !== "undefined";
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!hasIndexedDB()) {
      reject(new Error("IndexedDB unavailable"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "seq", autoIncrement: true });
      }
      if (!db.objectStoreNames.contains(DEAD)) {
        db.createObjectStore(DEAD, { keyPath: "seq", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(store, mode);
        const req = fn(t.objectStore(store));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
        t.oncomplete = () => db.close();
      }),
  );
}

// --- Subscribable count (drives the "N en attente" badge) ---------------------

const listeners = new Set<() => void>();
let cachedCount = 0;

function emit() {
  for (const l of listeners) l();
}

export function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

// Synchronous snapshot for useSyncExternalStore; refreshed by refreshCount().
export function getCountSnapshot(): number {
  return cachedCount;
}

export async function refreshCount(): Promise<number> {
  if (!hasIndexedDB()) {
    cachedCount = 0;
    emit();
    return 0;
  }
  cachedCount = await tx<number>(STORE, "readonly", (s) => s.count());
  emit();
  return cachedCount;
}

// --- Public queue API ---------------------------------------------------------

export async function enqueueStatus(deliveryId: string, body: StatusBody): Promise<void> {
  await tx(STORE, "readwrite", (s) =>
    s.add({ kind: "status", deliveryId, body, createdAt: Date.now(), attempts: 0 } satisfies StatusItem),
  );
  await refreshCount();
}

export async function enqueueProof(input: {
  deliveryId: string;
  photo?: Blob;
  signature?: Blob;
  lat?: number;
  lon?: number;
}): Promise<void> {
  const item: ProofItem = {
    kind: "proof",
    deliveryId: input.deliveryId,
    lat: input.lat,
    lon: input.lon,
    createdAt: Date.now(),
    attempts: 0,
  };
  if (input.photo) {
    item.photoBuf = await input.photo.arrayBuffer();
    item.photoType = input.photo.type || "image/jpeg";
  }
  if (input.signature) {
    item.sigBuf = await input.signature.arrayBuffer();
    item.sigType = input.signature.type || "image/png";
  }
  await tx(STORE, "readwrite", (s) => s.add(item));
  await refreshCount();
}

async function getAll(): Promise<Required<QueueItem>[]> {
  // The store is keyed by an autoincrement seq, so getAll() yields FIFO order.
  return tx<Required<QueueItem>[]>(STORE, "readonly", (s) => s.getAll() as IDBRequest<Required<QueueItem>[]>);
}

async function remove(seq: number): Promise<void> {
  await tx(STORE, "readwrite", (s) => s.delete(seq));
}

async function moveToDead(item: Required<QueueItem>): Promise<void> {
  await tx(DEAD, "readwrite", (s) => s.add(item));
  await remove(item.seq);
}

// --- Token refresh (queued items may outlive a ~15 min access token) ----------

let refreshing: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  // Collapse concurrent refreshes into one in-flight request.
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (!refreshToken) return false;
    try {
      const data = await apiFetch<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/refresh",
        { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
      );
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

// --- Replay -------------------------------------------------------------------

async function send(item: Required<QueueItem>): Promise<void> {
  if (item.kind === "status") {
    await apiFetch(`/api/v1/driver/deliveries/${item.deliveryId}/status`, {
      method: "PUT",
      body: JSON.stringify(item.body),
    });
    return;
  }
  const form = new FormData();
  if (item.photoBuf) form.append("photo", new Blob([item.photoBuf], { type: item.photoType }), "photo.jpg");
  if (item.sigBuf) form.append("signature", new Blob([item.sigBuf], { type: item.sigType }), "signature.png");
  if (item.lat != null) form.append("lat", String(item.lat));
  if (item.lon != null) form.append("lon", String(item.lon));
  await apiUpload(`/api/v1/driver/deliveries/${item.deliveryId}/proof`, form);
}

let flushing = false;

// Replay queued mutations in order. Returns true when the queue fully drained.
// Stops early (leaving items queued) on a network failure or a failed refresh —
// the next `online` event or manual call retries.
export async function flushQueue(): Promise<boolean> {
  if (flushing) return false;
  if (typeof navigator !== "undefined" && navigator.onLine === false) return false;
  flushing = true;
  try {
    const items = await getAll();
    for (const item of items) {
      try {
        await send(item);
        await remove(item.seq);
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          // Token likely expired while offline — refresh once, then retry it.
          if (await refreshAccessToken()) {
            try {
              await send(item);
              await remove(item.seq);
              continue;
            } catch {
              return false; // still failing after refresh — stop, keep queued.
            }
          }
          return false; // no/failed refresh — cannot sync now.
        }
        if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          await moveToDead(item); // permanent rejection — park it, keep going.
          continue;
        }
        return false; // network error or 5xx — stop, retry later.
      }
    }
    return true;
  } finally {
    flushing = false;
    await refreshCount();
  }
}

// Register the reconnect trigger once per app load.
let started = false;
export function startOfflineSync(): void {
  if (started || typeof window === "undefined" || !hasIndexedDB()) return;
  started = true;
  window.addEventListener("online", () => void flushQueue());
  void refreshCount().then(() => void flushQueue());
}
