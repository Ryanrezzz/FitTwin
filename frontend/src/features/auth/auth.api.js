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
