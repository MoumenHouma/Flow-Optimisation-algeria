// Thin fetch wrapper around the RouteOpt API (docs/ARCHITECTURE.md §2.2).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...init.headers,
    },
  });

  if (response.status === 401) {
    // Session expired/invalid — drop it and bounce to login.
    localStorage.removeItem("access_token");
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}
