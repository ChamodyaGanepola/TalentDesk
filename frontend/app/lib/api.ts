const configuredApi = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "");
const configuredWs = process.env.NEXT_PUBLIC_WS_URL?.trim().replace(/\/$/, "");

function isLocalHost(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

/** API base URL. On Vercel you must set NEXT_PUBLIC_API_URL to your public backend (e.g. ngrok). */
export function getApiBase(): string {
  if (configuredApi) return configuredApi;
  if (isLocalHost()) return "http://127.0.0.1:8000";
  return "";
}

/** WebSocket base URL. On Vercel set NEXT_PUBLIC_WS_URL to wss://your-public-backend */
export function getWsBase(): string {
  if (configuredWs) return configuredWs;
  if (isLocalHost()) return "ws://127.0.0.1:8000";
  return "";
}

export const API = configuredApi || (typeof window === "undefined" ? "" : getApiBase());
export const WS = configuredWs || (typeof window === "undefined" ? "" : getWsBase());

export function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    "ngrok-skip-browser-warning": "true",
    ...extra,
  };
}

/** Safe fetch against the API. Returns null if URL missing or network fails. */
export async function apiFetch(
  path: string,
  init?: RequestInit
): Promise<Response | null> {
  const api = getApiBase();
  if (!api) return null;

  const url = path.startsWith("http") ? path : `${api}${path.startsWith("/") ? path : `/${path}`}`;

  try {
    return await fetch(url, init);
  } catch {
    return null;
  }
}
