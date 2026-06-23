import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "./stores/auth";
import AppShell from "./components/AppShell.jsx";
import AuthPage from "./features/auth/AuthPage.jsx";
import OnboardingPage from "./features/onboarding/OnboardingPage.jsx";
import DashboardPage from "./features/dashboard/DashboardPage.jsx";
import CoachPage from "./features/coach/CoachPage.jsx";

function Protected({ children }) {
  const token = useAuthStore((s) => s.accessToken);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/profile" element={<OnboardingPage />} />
        <Route path="/coach" element={<CoachPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
