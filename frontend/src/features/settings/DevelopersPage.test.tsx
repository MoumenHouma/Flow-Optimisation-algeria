import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DevelopersPage } from "@/features/settings/DevelopersPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("DevelopersPage", () => {
  it("creates an API key and reveals the plaintext once", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/integrations/api-keys": () => ({ body: [] }),
      "GET /api/v1/integrations/webhooks": () => ({ body: [] }),
      "POST /api/v1/integrations/api-keys": () => ({
        status: 201,
        body: {
          id: "k1",
          name: "Shopify",
          key_prefix: "rk_live_ab12",
          scope: "write",
          last_used_at: null,
          revoked_at: null,
          created_at: "2026-07-21T10:00:00Z",
          key: "rk_live_ab1234567890abcdef",
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<DevelopersPage />, { route: "/developers" });

    await waitFor(() => expect(screen.getByText("Clés API")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/Shopify/i), "Shopify");
    await user.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/integrations/api-keys"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    // The one-time plaintext key is shown.
    await waitFor(() => expect(screen.getByText("rk_live_ab1234567890abcdef")).toBeInTheDocument());
  });

  it("registers a webhook", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/integrations/api-keys": () => ({ body: [] }),
      "GET /api/v1/integrations/webhooks": () => ({ body: [] }),
      "POST /api/v1/integrations/webhooks": () => ({
        status: 201,
        body: {
          id: "w1",
          url: "https://shop.dz/hook",
          events: ["delivery.status_changed"],
          active: true,
          created_at: "2026-07-21T10:00:00Z",
          secret: "abc123",
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<DevelopersPage />, { route: "/developers" });

    await waitFor(() => expect(screen.getByText("Webhooks")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/mon-site\.dz/i), "https://shop.dz/hook");
    await user.click(screen.getByRole("button", { name: /ajouter le webhook/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/integrations/webhooks"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    await waitFor(() => expect(screen.getByText("abc123")).toBeInTheDocument());
  });
});
