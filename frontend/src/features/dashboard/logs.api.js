import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { qk } from "../../lib/queryKeys";

/** GET /logs/today — water / steps / workout for the current day. */
export function useTodayLog(enabled = true) {
  return useQuery({
    queryKey: qk.todayLog,
    queryFn: () => api("/logs/today"),
    enabled,
  });
}

/** GET /logs/history — recent logged days for the activity calendar. */
export function useLogHistory(days = 7, enabled = true) {
  return useQuery({
    queryKey: qk.logHistory,
    queryFn: () => api(`/logs/history?days=${days}`),
    enabled,
  });
}

/** PUT /logs/today — partial update; refreshes today's log + dashboard + history. */
export function useUpdateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch) => api("/logs/today", { method: "PUT", body: patch }),
    onSuccess: (data) => {
      queryClient.setQueryData(qk.todayLog, data);
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
      queryClient.invalidateQueries({ queryKey: qk.logHistory });
    },
  });
}
