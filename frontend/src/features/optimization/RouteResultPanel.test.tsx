import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RouteResultPanel } from "@/features/optimization/RouteResultPanel";
import { mockFetch, renderWithProviders } from "@/test-utils";
import type { JobResult } from "@/types";

afterEach(() => vi.unstubAllGlobals());

const JOB: JobResult = {
  job_id: "j1",
  status: "completed",
  solver_strategy: "or_tools",
  total_distance_m: 3000,
  route_ids: ["r1"],
};

const ROUTE = {
  id: "r1",
  vehicle_id: "v1",
  total_distance_m: 3000,
  total_time_s: 900,
  status: "in_progress",
  depot: { lat: 36.75, lon: 3.05 },
  geometry: null,
  stops: [
    { delivery_id: "d1", sequence: 0, address: "A", lat: 36.75, lon: 3.06 },
    { delivery_id: "d2", sequence: 1, address: "B", lat: 36.76, lon: 3.07 },
  ],
};

describe("RouteResultPanel re-optimize", () => {
  it("triggers re-optimization and polls the job", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/routes/r1": () => ({ body: ROUTE }),
      "POST /api/v1/routes/r1/reoptimize": () => ({
        status: 202,
        body: { job_id: "j2", status: "pending", estimated_duration_ms: 1000 },
      }),
      "GET /api/v1/routes/jobs/j2": () => ({
        body: { job_id: "j2", status: "completed", route_ids: ["r1"] },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<RouteResultPanel job={JOB} />);

    await waitFor(() => expect(screen.getByText(/véhicule 1/i)).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /ré-optimiser/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/routes/r1/reoptimize"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    // The returned job is polled to completion.
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/routes/jobs/j2"),
        expect.anything(),
      ),
    );
  });
});
