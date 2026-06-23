import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Auth token store. The access token is short-lived; the refresh token rotates a
 * new access token via /auth/refresh. Persisted to localStorage so a reload keeps
 * the session. (httpOnly cookies would be the V1.5 hardening.)
 */
export const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      setTokens: ({ access_token, refresh_token }) =>
        set((s) => ({
          accessToken: access_token ?? s.accessToken,
          refreshToken: refresh_token ?? s.refreshToken,
        })),
      clear: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: "fittwin-auth" },
  ),
);

export const isLoggedIn = () => Boolean(useAuthStore.getState().accessToken);
