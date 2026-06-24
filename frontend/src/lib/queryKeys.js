// Centralized query keys so mutations can invalidate precisely.
export const qk = {
  me: ["me"],
  profile: ["profile"],
  activePlan: ["plan", "active"],
  plan: (id) => ["plan", id],
  dashboard: ["dashboard", "summary"],
};
