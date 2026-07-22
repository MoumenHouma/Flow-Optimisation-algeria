import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

const PERF = {
  range_days: 30,
  delivered: 8,
  failed: 2,
  success_rate: 0.8,
  total_distance_m: 12000,
  routes: 3,
  avg_distance_per_route_m: 4000,
  failure_reasons: [{ reason: "client_absent", count: 2 }],
  drivers: [{ driver_id: "u1", driver_name: "Amine", delivered: 8, failed: 2 }],
};

const TRENDS = {
  days: 30,
  points: [
    {
      date: "2026-07-19",
      deliveries_completed: 5,
      deliveries_failed: 1,
      routes: 2,
      distance_m: 8000,
    },
    {
      date: "2026-07-20",
      deliveries_completed: 3,
      deliveries_failed: 1,
      routes: 1,
      distance_m: 4000,
    },
  ],
};

describe("AnalyticsPage", () => {
  it("renders KPIs, failure reasons and the driver leaderboard", async () => {
    mockFetch({
      "GET /api/v1/analytics/performance": () => ({ body: PERF }),
      "GET /api/v1/analytics/trends": () => ({ body: TRENDS }),
    });
    renderWithProviders(<AnalyticsPage />, { route: "/analytics" });

    await waitFor(() => expect(screen.getByText("Amine")).toBeInTheDocument());
    // 80% shows as both the success-rate KPI and the driver's success column.
    expect(screen.getAllByText("80%").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("client_absent")).toBeInTheDocument();
    expect(screen.getByText("Taux de réussite")).toBeInTheDocument();
  });

  it("refetches when the range changes", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/analytics/performance": () => ({ body: PERF }),
      "GET /api/v1/analytics/trends": () => ({ body: TRENDS }),
    });
    const user = userEvent.setup();
    renderWithProviders(<AnalyticsPage />, { route: "/analytics" });

    await waitFor(() => expect(screen.getByText("Amine")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "7 j" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/analytics/performance?days=7"),
        expect.anything(),
      ),
    );
  });
});
