import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { qk } from "../../lib/queryKeys";

/**
 * POST /meals/rotate — swap ONE slot's dish for today ("not fish tonight").
 * The server persists how far each slot has rotated, so the swap survives a
 * reload; we just refetch the summary rather than patching state locally.
 */
export function useRotateMeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (slot) => api("/meals/rotate", { method: "POST", body: { slot } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.dashboard }),
  });
}

/** POST /meals/rotate/reset — back to the coach's original picks for today. */
export function useResetRotations() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api("/meals/rotate/reset", { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: qk.dashboard }),
  });
}
