import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { AuditEntry } from "@/types";

// Company audit trail (H2), newest first. Admin-only server-side; an optional
// action filter narrows to a single event type.
export function useAuditLog(action?: string) {
  return useQuery({
    queryKey: ["audit-log", action ?? "all"],
    queryFn: () => {
      const qs = action ? `?action=${encodeURIComponent(action)}` : "";
      return apiFetch<AuditEntry[]>(`/api/v1/audit-log${qs}`);
    },
  });
}
