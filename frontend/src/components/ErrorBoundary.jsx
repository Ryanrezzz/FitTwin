import React from "react";
import { AlertTriangle } from "lucide-react";
import { Button, Card } from "./ui.jsx";

/**
 * Catches render-time crashes so one bad component can't blank the whole app.
 *
 * Without this, any thrown error in the tree unmounts everything and the user
 * is left staring at a white page with no way forward — the worst failure mode
 * for a live product, because it looks like the site is simply down.
 *
 * React only surfaces render errors to class components, so this stays a class.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep the details in the console for debugging; the user gets plain words.
    console.error("Unhandled UI error:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="grid min-h-screen place-items-center bg-bone p-6">
        <Card className="max-w-md text-center">
          <AlertTriangle className="mx-auto size-8 text-coral" aria-hidden="true" />
          <h1 className="mt-3 font-display text-xl font-bold">This page stopped responding</h1>
          <p className="mt-2 text-sm text-ink-soft">
            Something broke while drawing this screen. Your data is safe — reloading
            usually fixes it.
          </p>
          <div className="mt-5 flex justify-center gap-2">
            <Button onClick={() => window.location.reload()}>Reload</Button>
            <Button variant="outline" onClick={() => { window.location.href = "/"; }}>
              Go to dashboard
            </Button>
          </div>
          {import.meta.env.DEV && (
            <pre className="mt-4 max-h-40 overflow-auto rounded-[10px] bg-ink/5 p-3 text-left text-xs text-ink-soft">
              {String(this.state.error?.stack || this.state.error)}
            </pre>
          )}
        </Card>
      </div>
    );
  }
}
