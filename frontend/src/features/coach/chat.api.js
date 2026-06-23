import { api } from "../../lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { qk } from "../../lib/queryKeys";

/** POST /chat — profile + active plan are read server-side; we just send the message. */
export function useSendChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (message) => api("/chat", { method: "POST", body: { message } }),
    onSuccess: (res) => {
      // a chat turn can adapt + persist a new plan version → refresh the dashboard
      if (res?.plan_version) queryClient.invalidateQueries({ queryKey: qk.activePlan });
    },
  });
}
