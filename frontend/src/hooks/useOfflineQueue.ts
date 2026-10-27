import { useSyncExternalStore } from "react";

import { flushQueue, getCountSnapshot, subscribe } from "@/lib/offline-queue";

// Reactive count of pending offline mutations, plus a manual flush trigger.
// Drives the Driver PWA's "N en attente" badge (Phase D).
export function useOfflineQueue(): { pending: number; flush: () => void } {
  const pending = useSyncExternalStore(subscribe, getCountSnapshot, getCountSnapshot);
  return { pending, flush: () => void flushQueue() };
}
