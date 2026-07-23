import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LiveTrackingPage } from "@/features/tracking/LiveTrackingPage";
import { renderWithProviders } from "@/test-utils";

// The SSE-over-fetch hook is exercised at the api layer; here we stub it to
// verify the page renders streamed positions.
vi.mock("@/api/tracking", () => ({
  useLivePositions: () => ({
    positions: [{ vehicle_id: "abc1234567", lat: 36.7412, lon: 3.0511, ts: Date.now() / 1000 }],
    connected: true,
  }),
}));

describe("LiveTrackingPage", () => {
  it("renders live vehicle positions and a connected indicator", () => {
    renderWithProviders(<LiveTrackingPage />, { route: "/tracking" });

    expect(screen.getByText("Connecté")).toBeInTheDocument();
    expect(screen.getByText(/abc12345/)).toBeInTheDocument();
    expect(screen.getByText(/36.74120/)).toBeInTheDocument();
  });
});
