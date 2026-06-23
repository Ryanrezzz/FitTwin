import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Dumbbell } from "lucide-react";
import { Button, Card, Field, Input } from "../../components/ui.jsx";
import { login, register } from "./auth.api";

export default function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isRegister) await register({ email, password });
      await login({ email, password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 420, damping: 32 }}
        className="w-full max-w-sm"
      >
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <span className="grid size-12 place-items-center rounded-[14px] bg-volt text-ink">
            <Dumbbell className="size-6" strokeWidth={2.5} />
          </span>
          <h1 className="font-display text-3xl font-extrabold tracking-tight">FitTwin</h1>
          <p className="text-sm text-ink-soft">Your digital training twin.</p>
        </div>

        <Card>
          <form onSubmit={onSubmit} className="space-y-4">
            <Field label="Email">
              <Input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Password" hint={isRegister ? "At least 8 characters." : undefined}>
              <Input
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
                minLength={isRegister ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </Field>

            {error && <p className="text-sm text-coral">{error}</p>}

            <Button type="submit" loading={busy} className="w-full">
              {isRegister ? "Create account" : "Log in"}
            </Button>
          </form>

          <p className="mt-4 text-center text-sm text-ink-soft">
            {isRegister ? "Already have an account?" : "New to FitTwin?"}{" "}
            <button
              type="button"
              className="font-semibold text-ink underline-offset-2 hover:underline"
              onClick={() => {
                setMode(isRegister ? "login" : "register");
                setError(null);
              }}
            >
              {isRegister ? "Log in" : "Create one"}
            </button>
          </p>
        </Card>
      </motion.div>
    </div>
  );
}
