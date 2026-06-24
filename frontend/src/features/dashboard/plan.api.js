import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../../lib/api";
import { qk } from "../../lib/queryKeys";

/** GET /plans/active — null when no plan has been generated yet (404). */
export function useActivePlan() {
  return useQuery({
    queryKey: qk.activePlan,
    queryFn: async () => {
      try {
        return await api("/plans/active");
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useGeneratePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api("/plans/generate", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.activePlan });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
    },
  });
}

/** GET /dashboard/summary — calculated overview cards + the hybrid agent map. */
export function useDashboardSummary(enabled = true) {
  return useQuery({
    queryKey: qk.dashboard,
    queryFn: () => api("/dashboard/summary"),
    enabled,
  });
}
