import { create } from "zustand";
import { persist } from "zustand/middleware";

// Auth session state (docs/ARCHITECTURE.md §5.1). Tokens persist to localStorage
// so the api-client can attach the access token to requests.
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  setTokens: (access: string, refresh: string) => void;
  clear: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      setTokens: (access, refresh) => {
        localStorage.setItem("access_token", access);
        set({ accessToken: access, refreshToken: refresh });
      },
      clear: () => {
        localStorage.removeItem("access_token");
        set({ accessToken: null, refreshToken: null });
      },
      isAuthenticated: () => Boolean(get().accessToken),
    }),
    { name: "routeopt-auth" },
  ),
);
