import { Route, Routes } from "react-router-dom";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TrackPage } from "@/features/track/TrackPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

function renderTrack(token: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/track/:token" element={<TrackPage />} />
    </Routes>,
    { route: `/track/${token}` },
  );
}

describe("TrackPage", () => {
  it("shows the delivery status and live position", async () => {
    mockFetch({
      "GET /api/v1/track/tok123": () => ({
        body: {
          order_id: "CMD-9",
          status: "en_route",
          vehicle_position: { vehicle_id: "v1", lat: 36.74, lon: 3.05, ts: 1 },
        },
      }),
    });
    renderTrack("tok123");

    await waitFor(() => expect(screen.getByText("En cours de livraison")).toBeInTheDocument());
    expect(screen.getByText("Commande CMD-9")).toBeInTheDocument();
    expect(screen.getByText(/36.7400/)).toBeInTheDocument();
  });

  it("shows an error for an invalid link", async () => {
    mockFetch({
      "GET /api/v1/track/bad": () => ({ status: 404 }),
    });
    renderTrack("bad");

    await waitFor(() => expect(screen.getByText(/Lien de suivi invalide/)).toBeInTheDocument());
  });
});
