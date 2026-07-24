import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "@/features/auth/LoginPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("LoginPage", () => {
  it("submits credentials and stores the token on success", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/auth/login": () => ({
        body: { access_token: "tok-123", refresh_token: "ref-456", token_type: "bearer" },
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: "/login" });

    await user.type(screen.getByLabelText("Email"), "k@acme.dz");
    await user.type(screen.getByLabelText("Mot de passe"), "supersecret");
    await user.click(screen.getByRole("button", { name: /se connecter/i }));

    await waitFor(() => expect(localStorage.getItem("access_token")).toBe("tok-123"));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/login"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows an error when login fails", async () => {
    // 500 (not 401) so we exercise the error UI without the 401 redirect path.
    mockFetch({ "POST /api/v1/auth/login": () => ({ status: 500, body: { detail: "nope" } }) });
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: "/login" });

    await user.type(screen.getByLabelText("Email"), "k@acme.dz");
    await user.type(screen.getByLabelText("Mot de passe"), "wrongpass");
    await user.click(screen.getByRole("button", { name: /se connecter/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/invalide/i));
    expect(localStorage.getItem("access_token")).toBeNull();
  });
});
