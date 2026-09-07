import { api } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";

export async function register({ email, password }) {
  return api("/auth/register", { method: "POST", body: { email, password } });
}

export async function login({ email, password }) {
  const tokens = await api("/auth/login", { method: "POST", body: { email, password } });
  useAuthStore.getState().setTokens(tokens);
  return tokens;
}

/** GET /auth/google/config — is Google sign-in enabled, and its public client id. */
export async function googleConfig() {
  return api("/auth/google/config");
}

/**
 * POST /auth/google — exchange a Google ID token for our own session tokens.
 * The credential is verified server-side; nothing here is trusted.
 */
export async function googleSignIn(credential) {
  const tokens = await api("/auth/google", { method: "POST", body: { credential } });
  useAuthStore.getState().setTokens(tokens);
  return tokens;
}
