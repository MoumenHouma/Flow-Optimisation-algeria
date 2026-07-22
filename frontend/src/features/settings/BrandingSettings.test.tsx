import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BrandingSettings } from "@/features/settings/BrandingSettings";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => vi.unstubAllGlobals());

describe("BrandingSettings", () => {
  it("loads current branding and saves an update", async () => {
    const fetchMock = mockFetch({
      "GET /api/v1/company": () => ({
        body: {
          id: "c1",
          name: "Acme",
          plan: "pro",
          locale: "fr",
          branding: { brand_name: "Acme" },
        },
      }),
      "PUT /api/v1/company/branding": () => ({
        body: {
          id: "c1",
          name: "Acme",
          plan: "pro",
          locale: "fr",
          branding: { brand_name: "Neo" },
        },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<BrandingSettings />);

    const nameInput = await screen.findByPlaceholderText("RouteOpt");
    await waitFor(() => expect(nameInput).toHaveValue("Acme"));

    await user.clear(nameInput);
    await user.type(nameInput, "Neo");
    await user.click(screen.getByRole("button", { name: /enregistrer/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/company/branding"),
        expect.objectContaining({ method: "PUT" }),
      ),
    );
  });
});
