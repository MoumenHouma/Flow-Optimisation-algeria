import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuditLogPage } from "@/features/settings/AuditLogPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("AuditLogPage", () => {
  it("renders audit entries", async () => {
    mockFetch({
      "GET /api/v1/audit-log": () => ({
        body: [
          {
            id: 2,
            action: "user.login",
            resource_type: "user",
            resource_id: "abcdef12-0000-0000-0000-000000000000",
            actor_user_id: "abcdef12-0000-0000-0000-000000000000",
            metadata: {},
            ip_address: "41.100.0.1",
            created_at: "2026-07-22T09:00:00+00:00",
          },
        ],
      }),
    });
    renderWithProviders(<AuditLogPage />, { route: "/audit-log" });

    await waitFor(() => expect(screen.getByText("user.login")).toBeInTheDocument());
    expect(screen.getByText("41.100.0.1")).toBeInTheDocument();
  });

  it("shows an access-denied message on error", async () => {
    mockFetch({
      "GET /api/v1/audit-log": () => ({ status: 403, body: { detail: "Forbidden" } }),
    });
    renderWithProviders(<AuditLogPage />, { route: "/audit-log" });

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/administrateurs/i));
  });
});
