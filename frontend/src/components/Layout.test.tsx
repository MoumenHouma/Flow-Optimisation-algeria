import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Layout } from "@/components/Layout";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("Layout", () => {
  it("renders navigation to every section + logout", () => {
    mockFetch({ "GET /api/v1/company": () => ({ body: { branding: null } }) });
    renderWithProviders(<Layout />);
    expect(screen.getByRole("link", { name: /tableau de bord/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /importer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /optimiser/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /flotte/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /territoires/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analytics/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /déconnexion/i })).toBeInTheDocument();
  });

  it("applies the company brand name (F16 white-label)", async () => {
    mockFetch({
      "GET /api/v1/company": () => ({
        body: { branding: { brand_name: "Livraison Express", primary_color: "#EF4444" } },
      }),
    });
    renderWithProviders(<Layout />);
    await waitFor(() => expect(screen.getByText(/Livraison Express/)).toBeInTheDocument());
  });
});
