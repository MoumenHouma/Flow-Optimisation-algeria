import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OptimizationPage } from "@/features/optimization/OptimizationPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("OptimizationPage", () => {
  it("submits the selected objective preset (F14)", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/fleet/vehicles": () => ({
        body: [
          {
            id: "v1",
            name: "V",
            vehicle_type: "van",
            capacity_weight: 500,
            depot: {},
            active: true,
          },
        ],
      }),
      "GET /api/v1/orders": () => ({ body: [{ id: "d1", address: "A", status: "geocoded" }] }),
      "POST /api/v1/routes/optimize": () => ({
        status: 202,
        body: { job_id: "j1", status: "pending", estimated_duration_ms: 1000 },
      }),
      "GET /api/v1/routes/jobs/j1": () => ({
        body: { job_id: "j1", status: "running", route_ids: [] },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<OptimizationPage />);

    await user.click(screen.getByRole("button", { name: "Écologique" }));
    await user.click(screen.getByRole("button", { name: /optimiser la tournée/i }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find((c) => String(c[0]).includes("/routes/optimize"));
      expect(call).toBeTruthy();
      const body = JSON.parse((call![1] as RequestInit).body as string);
      expect(body.objective).toEqual({ distance: 0.2, time: 0.2, fuel: 3, co2: 2 });
    });
  });
});
