import { useAuthStore } from "../stores/auth";

// Empty base in dev → Vite proxies /api to the backend. Set VITE_API_BASE_URL in prod.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const PREFIX = `${BASE}/api/v1`;

/** Error carrying the backend's normalized envelope { code, message, request_id }. */
export class ApiError extends Error {
  constructor(status, body) {
    const detail = body?.error?.message || body?.detail || `Request failed (${status})`;
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.error?.code;
    this.requestId = body?.error?.request_id;
  }
}

async function parse(res) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function authHeaders(extra) {
  const { accessToken } = useAuthStore.getState();
  const headers = { ...extra };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return headers;
}

let refreshing = null;

/** Swap the refresh token for a fresh access token. De-duped across concurrent 401s. */
async function tryRefresh() {
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) return false;
  if (!refreshing) {
    refreshing = (async () => {
      const res = await fetch(`${PREFIX}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clear();
        return false;
      }
      const body = await parse(res);
      setTokens({ access_token: body.access_token });
      return true;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/**
 * Single choke point for API calls. Adds the bearer token, retries once after a
 * refresh on 401, and throws ApiError with the backend envelope on failure.
 */
export async function api(path, { method = "GET", body, headers, _retried } = {}) {
  const init = { method, headers: authHeaders(headers) };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  const res = await fetch(`${PREFIX}${path}`, init);

  if (res.status === 401 && !_retried && (await tryRefresh())) {
    return api(path, { method, body, headers, _retried: true });
  }
  if (!res.ok) throw new ApiError(res.status, await parse(res));
  return parse(res);
}
