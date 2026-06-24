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

/** PUT /logs/today — partial update; refreshes today's log + the dashboard cards. */
export function useUpdateLog() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch) => api("/logs/today", { method: "PUT", body: patch }),
    onSuccess: (data) => {
      queryClient.setQueryData(qk.todayLog, data);
      queryClient.invalidateQueries({ queryKey: qk.dashboard });
    },
  });
}
