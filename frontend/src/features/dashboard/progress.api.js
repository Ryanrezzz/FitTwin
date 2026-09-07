import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { qk } from "../../lib/queryKeys";

/** GET /progress/weight — recent weigh-ins, newest first, plus the net change. */
export function useWeightSeries(days = 60, enabled = true) {
  return useQuery({
    queryKey: qk.weightSeries,
    queryFn: () => api(`/progress/weight?days=${days}`),
    enabled,
  });
}

/**
 * PUT /progress/weight — record today's weigh-in.
 * Invalidates the dashboard too: current weight, weeks-to-goal and the calorie
 * target are all derived from the latest entry.
 */
export function useLogWeight() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (weight_kg) => api("/progress/weight", { method: "PUT", body: { weight_kg } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.weightSeries });
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
    },
  });
}
