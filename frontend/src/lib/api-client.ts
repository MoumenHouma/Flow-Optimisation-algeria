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

// suppressAuthRedirect: on 401, throw ApiError(401) WITHOUT clearing the token or
// navigating to /login. The offline-queue replay path needs this so it can catch
// the 401 and refresh the access token instead of being bounced mid-sync.
export interface ApiOptions {
  suppressAuthRedirect?: boolean;
}

function handle401(opts: ApiOptions): never {
  if (!opts.suppressAuthRedirect) {
    localStorage.removeItem("access_token");
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }
  throw new ApiError(401, "Unauthorized");
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  opts: ApiOptions = {},
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...init.headers,
    },
  });

  if (response.status === 401) handle401(opts);

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T; // e.g. DELETE
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// Multipart upload — never set Content-Type so the browser adds the boundary.
export async function apiUpload<T>(path: string, form: FormData, opts: ApiOptions = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: authHeader(),
    body: form,
  });

  if (response.status === 401) handle401(opts);
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
