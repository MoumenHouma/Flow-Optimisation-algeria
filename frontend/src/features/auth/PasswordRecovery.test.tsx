import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { mockFetch, renderWithProviders } from "@/test-utils";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("ForgotPasswordPage", () => {
  it("posts the email and confirms without revealing whether it exists", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/auth/forgot-password": () => ({ status: 202, body: null }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password" });

    await user.type(screen.getByLabelText("Email"), "k@acme.dz");
    await user.click(screen.getByRole("button", { name: /envoyer le lien/i }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/si un compte existe/i));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/forgot-password"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("surfaces a throttled request instead of a false confirmation", async () => {
    mockFetch({
      "POST /api/v1/auth/forgot-password": () => ({ status: 429, body: { detail: "slow down" } }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ForgotPasswordPage />, { route: "/forgot-password" });

    await user.type(screen.getByLabelText("Email"), "k@acme.dz");
    await user.click(screen.getByRole("button", { name: /envoyer le lien/i }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/impossible/i));
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("ResetPasswordPage", () => {
  it("sends the token from the query string with the new password", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/auth/reset-password": () => ({ status: 204, body: null }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password?token=abc123" });

    await user.type(screen.getByLabelText("Mot de passe"), "brand-new-secret");
    await user.type(screen.getByLabelText("Confirmer le mot de passe"), "brand-new-secret");
    await user.click(screen.getByRole("button", { name: /changer le mot de passe/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/reset-password"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ token: "abc123", password: "brand-new-secret" }),
        }),
      ),
    );
  });

  it("blocks mismatched confirmations before hitting the API", async () => {
    const fetchMock = mockFetch({
      "POST /api/v1/auth/reset-password": () => ({ status: 204, body: null }),
    });
    const user = userEvent.setup();
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password?token=abc123" });

    await user.type(screen.getByLabelText("Mot de passe"), "brand-new-secret");
    await user.type(screen.getByLabelText("Confirmer le mot de passe"), "something-else");
    await user.click(screen.getByRole("button", { name: /changer le mot de passe/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/ne correspondent pas/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses a link with no token", () => {
    mockFetch({});
    renderWithProviders(<ResetPasswordPage />, { route: "/reset-password" });

    expect(screen.getByRole("alert")).toHaveTextContent(/incomplet/i);
    expect(screen.queryByLabelText("Mot de passe")).toBeNull();
  });
});
