export type AuthUser = {
  name: string;
  email: string;
};

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "user";
const REMEMBER_EMAIL_KEY = "remember_email";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);

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
  const headers: Record<string, string> = {
    "ngrok-skip-browser-warning": "true",
    ...extra,
  };

  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

let refreshPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API}/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

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
  const token = getAccessToken();
  if (!token) return null;

  let res = await fetch(`${API}/auth/me`, {
    headers: getAuthHeaders(),
  });

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      clearSession();
      return null;
    }

    res = await fetch(`${API}/auth/me`, {
      headers: getAuthHeaders(),
    });
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
}

export async function logoutSession(): Promise<void> {
  const accessToken = getAccessToken();
  const refreshToken = getRefreshToken();

  if (accessToken) {
    try {
      await fetch(`${API}/auth/logout`, {
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

// Backward compatibility
export const getToken = getAccessToken;
