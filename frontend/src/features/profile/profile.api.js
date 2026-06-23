import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import { qk } from "../../lib/queryKeys";

/** GET /profile — returns null (not an error) when onboarding isn't done yet. */
export function useProfile() {
  return useQuery({
    queryKey: qk.profile,
    queryFn: async () => {
      try {
        return await api("/profile");
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useSaveProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profile) => api("/profile", { method: "PUT", body: profile }),
    onSuccess: (data) => queryClient.setQueryData(qk.profile, data),
  });
}
