import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegisterPage } from "@/features/auth/RegisterPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("RegisterPage", () => {
  it("creates a company + admin and stores the token on success", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/auth/register": () => ({
        status: 201,
        body: { access_token: "tok-abc", refresh_token: "ref-def", token_type: "bearer" },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, { route: "/register" });

    await user.type(screen.getByLabelText("Nom de l'entreprise"), "Acme");
    await user.type(screen.getByLabelText("Votre nom"), "Khaled");
    await user.type(screen.getByLabelText("Email"), "k@acme.dz");
    await user.type(screen.getByLabelText("Mot de passe (min. 8)"), "supersecret");
    await user.click(screen.getByRole("button", { name: /créer mon compte/i }));

    await waitFor(() => expect(localStorage.getItem("access_token")).toBe("tok-abc"));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/register"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows an error when registration fails", async () => {
    mockFetch({
      "POST /api/v1/auth/register": () => ({ status: 409, body: { detail: "exists" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, { route: "/register" });

    await user.type(screen.getByLabelText("Nom de l'entreprise"), "Acme");
    await user.type(screen.getByLabelText("Votre nom"), "Khaled");
    await user.type(screen.getByLabelText("Email"), "dup@acme.dz");
    await user.type(screen.getByLabelText("Mot de passe (min. 8)"), "supersecret");
    await user.click(screen.getByRole("button", { name: /créer mon compte/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/impossible/i));
    expect(localStorage.getItem("access_token")).toBeNull();
  });
});
