import { apiFetch, apiHeaders, getApiBase } from "@/app/lib/api";

export type AuthUser = {
  name: string;
  email: string;
};

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "user";
const REMEMBER_EMAIL_KEY = "remember_email";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return (
    localStorage.getItem(ACCESS_TOKEN_KEY) ||
    localStorage.getItem("auth_token")
  );
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function setSession(
  accessToken: string,
  refreshToken: string,
  user: AuthUser
): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  localStorage.removeItem("auth_token");
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem("auth_token");
  localStorage.removeItem("remember_password");
}

export function getRememberedEmail(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REMEMBER_EMAIL_KEY);
}

export function setRememberedEmail(email: string): void {
  localStorage.setItem(REMEMBER_EMAIL_KEY, email);
}

export function clearRememberedEmail(): void {
  localStorage.removeItem(REMEMBER_EMAIL_KEY);
}

export function getAuthHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers = apiHeaders(extra);

  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Authenticated API fetch with one refresh+retry on 401.
 */
export async function authFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response | null> {
  const extraHeaders =
    init.headers && typeof init.headers === "object" && !(init.headers instanceof Headers)
      ? (init.headers as Record<string, string>)
      : {};

  const doFetch = () =>
    apiFetch(path, {
      ...init,
      headers: getAuthHeaders(extraHeaders),
    });

  let res = await doFetch();
  if (!res) return null;

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) return res;
    res = await doFetch();
  }

  return res;
}

let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  const api = getApiBase();
  const refreshToken = getRefreshToken();
  if (!api || !refreshToken) return false;

  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await apiFetch("/auth/refresh", {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res) {
        clearSession();
        return false;
      }

      const data = await res.json();
      if (!res.ok || !data.success || !data.access_token || !data.refresh_token) {
        clearSession();
        return false;
      }

      setSession(data.access_token, data.refresh_token, data.user);
      return true;
    } catch {
      clearSession();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const api = getApiBase();
  const token = getAccessToken();
  if (!api || !token) return null;

  try {
    let res = await apiFetch("/auth/me", {
      headers: getAuthHeaders(),
    });

    if (!res) {
      return getStoredUser();
    }

    if (res.status === 401) {
      const refreshed = await refreshAccessToken();
      if (!refreshed) {
        clearSession();
        return null;
      }

      res = await apiFetch("/auth/me", {
        headers: getAuthHeaders(),
      });
      if (!res) {
        return getStoredUser();
      }
    }

    if (!res.ok) {
      clearSession();
      return null;
    }

    const data = await res.json();
    if (!data?.user) {
      clearSession();
      return null;
    }

    const refreshToken = getRefreshToken();
    if (refreshToken) {
      setSession(getAccessToken()!, refreshToken, data.user);
    }

    return data.user as AuthUser;
  } catch {
    // Backend unreachable or network error — don't crash the app.
    return getStoredUser();
  }
}

export async function logoutSession(): Promise<void> {
  const api = getApiBase();
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();

  if (api && accessToken) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        headers: getAuthHeaders({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Still clear local session if the network call fails.
    }
  }

  clearSession();
}

export const getToken = getAccessToken;
