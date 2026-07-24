import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ServiceTimePanel } from "@/features/analytics/ServiceTimePanel";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("ServiceTimePanel", () => {
  it("shows the trained model summary and retrains", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/predictions/service-time": () => ({
        body: {
          trained: true,
          sample_count: 42,
          cohort_count: 7,
          global_median_s: 600,
          mae_seconds: 120,
          trained_at: "2026-07-22T10:00:00Z",
        },
      }),
      "POST /api/v1/predictions/service-time/train": () => ({
        body: {
          trained: true,
          sample_count: 50,
          cohort_count: 8,
          global_median_s: 600,
          mae_seconds: 110,
          trained_at: "2026-07-22T11:00:00Z",
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ServiceTimePanel />);

    await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument());
    expect(screen.getByText("10 min")).toBeInTheDocument(); // 600s global median

    await user.click(screen.getByRole("button", { name: /ré-entraîner/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/predictions/service-time/train"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    await waitFor(() => expect(screen.getByText("50")).toBeInTheDocument());
  });
});
