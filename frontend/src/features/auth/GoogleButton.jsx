import { useEffect, useRef, useState } from "react";
import { googleConfig, googleSignIn } from "./auth.api";

const GSI_SRC = "https://accounts.google.com/gsi/client";

/** Load the Google Identity Services script once, shared across mounts. */
let gsiPromise = null;
function loadGsi() {
  if (gsiPromise) return gsiPromise;
  gsiPromise = new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const el = document.createElement("script");
    el.src = GSI_SRC;
    el.async = true;
    el.defer = true;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error("Could not reach Google"));
    document.head.appendChild(el);
  });
  return gsiPromise;
}

/**
 * "Sign in with Google".
 *
 * Renders nothing when the server reports the feature is off, so a deployment
 * without GOOGLE_CLIENT_ID shows a clean password-only form rather than a button
 * that fails on click. The client id comes from the API for the same reason —
 * one source of configuration instead of a second build-time copy.
 */
export default function GoogleButton({ onSuccess, onError }) {
  const holder = useRef(null);
  const [state, setState] = useState("loading"); // loading | ready | disabled | error

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const cfg = await googleConfig();
        if (cancelled) return;
        if (!cfg.enabled || !cfg.client_id) return setState("disabled");

        await loadGsi();
        if (cancelled || !holder.current) return;

        window.google.accounts.id.initialize({
          client_id: cfg.client_id,
          callback: async ({ credential }) => {
            try {
              await googleSignIn(credential);
              onSuccess?.();
            } catch (err) {
              onError?.(err.message || "Google sign-in failed");
            }
          },
        });
        window.google.accounts.id.renderButton(holder.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          shape: "pill",
          text: "continue_with",
          logo_alignment: "center",
          width: 320,
        });
        setState("ready");
      } catch {
        if (!cancelled) setState("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [onSuccess, onError]);

  if (state === "disabled") return null;

  return (
    <div className="mt-5">
      <div className="flex items-center gap-3 text-xs text-ink-soft">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>

      <div className="mt-4 flex min-h-[44px] justify-center">
        {state === "error" ? (
          <p className="text-xs text-ink-soft">
            Google sign-in is unavailable right now — use your email and password.
          </p>
        ) : (
          <div ref={holder} />
        )}
      </div>
    </div>
  );
}
