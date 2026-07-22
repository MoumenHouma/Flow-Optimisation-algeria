import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface RegisterInput {
  companyName: string;
  email: string;
  password: string;
  fullName: string;
}

interface LoginInput {
  email: string;
  password: string;
}

// Register a company + admin user (docs/ARCHITECTURE.md §2.2 Auth Service).
export function useRegister() {
  const setTokens = useAuthStore((s) => s.setTokens);
  return useMutation({
    mutationFn: (input: RegisterInput) =>
      apiFetch<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          company_name: input.companyName,
          email: input.email,
          password: input.password,
          full_name: input.fullName,
        }),
      }),
    onSuccess: (data) => setTokens(data.access_token, data.refresh_token),
  });
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  return useMutation({
    mutationFn: (input: LoginInput) =>
      apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: (data) => setTokens(data.access_token, data.refresh_token),
  });
}

// Revoke the refresh-token family server-side (M3), then clear local state.
// Best-effort: a failed/absent server call still clears the client session.
export function useLogout() {
  const clear = useAuthStore((s) => s.clear);
  return useMutation({
    mutationFn: async () => {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          await apiFetch("/api/v1/auth/logout", {
            method: "POST",
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
        } catch {
          // Server unreachable or token already invalid — clear locally anyway.
        }
      }
    },
    onSettled: () => clear(),
  });
}
