import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Dumbbell, LayoutDashboard, LogOut, MessageSquare, UserRound } from "lucide-react";
import { useAuthStore } from "../stores/auth";
import { cn } from "./ui.jsx";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/coach", label: "AI Coach", icon: MessageSquare },
  { to: "/profile", label: "Profile", icon: UserRound },
];

export default function AppShell() {
  const navigate = useNavigate();
  const clear = useAuthStore((s) => s.clear);
  const qc = useQueryClient();

  function logout() {
    clear();
    qc.clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 border-b border-line bg-bone/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <div className="flex items-center gap-2 font-display text-lg font-extrabold tracking-tight">
            <span className="grid size-7 place-items-center rounded-[8px] bg-volt text-ink">
              <Dumbbell className="size-4" strokeWidth={2.5} />
            </span>
            FitTwin
          </div>

          <nav className="ml-4 flex items-center gap-1">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-[10px] px-3 py-2 text-sm font-medium transition",
                    isActive ? "bg-ink text-bone" : "text-ink-soft hover:bg-ink/5",
                  )
                }
              >
                <Icon className="size-4" />
                <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>

          <button
            onClick={logout}
            className="ml-auto flex items-center gap-2 rounded-[10px] px-3 py-2 text-sm font-medium text-ink-soft hover:bg-ink/5"
          >
            <LogOut className="size-4" />
            <span className="hidden sm:inline">Log out</span>
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
