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
  if (isLocalHost()) return "http://127.0.0.1:8010";
  return "";
}

/** WebSocket base URL. On Vercel set NEXT_PUBLIC_WS_URL to wss://your-public-backend */
export function getWsBase(): string {
  if (configuredWs) return configuredWs;
  if (isLocalHost()) return "ws://127.0.0.1:8010";
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

/** Parse FastAPI / app error payloads for user-visible messages. */
export function readApiErrorMessage(
  payload: unknown,
  fallback = "Request failed"
): string {
  if (!payload || typeof payload !== "object") return fallback;

  const record = payload as { detail?: unknown; message?: unknown };
  if (typeof record.message === "string" && record.message.trim()) {
    return record.message.trim();
  }

  const detail = record.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);
    if (parts.length) return parts.join(", ");
  }

  return fallback;
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
