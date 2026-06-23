// Small shared, dumb UI primitives, themed to the athletic tokens.
import { Loader2 } from "lucide-react";

export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function Button({ variant = "primary", className, disabled, loading, children, ...props }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-[12px] px-4 py-2.5 text-sm font-semibold " +
    "transition active:scale-[.98] disabled:opacity-50 disabled:pointer-events-none focus:outline-none " +
    "focus-visible:ring-2 focus-visible:ring-volt focus-visible:ring-offset-2 focus-visible:ring-offset-bone";
  const variants = {
    primary: "bg-volt text-ink hover:bg-volt-press",
    outline: "border border-ink/20 text-ink hover:bg-ink/5",
    coral: "bg-coral text-white hover:opacity-90",
    ghost: "text-ink-soft hover:bg-ink/5",
  };
  return (
    <button className={cn(base, variants[variant], className)} disabled={disabled || loading} {...props}>
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Card({ className, children }) {
  return (
    <div
      className={cn(
        "rounded-card border border-line bg-paper p-5 shadow-[0_1px_2px_rgba(14,15,12,.06),0_8px_24px_rgba(14,15,12,.06)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Field({ label, children, hint, error }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-soft">{label}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-ink-soft/80">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-coral">{error}</span>}
    </label>
  );
}

export function Input(props) {
  return (
    <input
      {...props}
      className={cn(
        "w-full rounded-[12px] border border-line bg-bone px-3 py-2.5 text-sm text-ink",
        "placeholder:text-ink-soft/60 focus:border-volt-press focus:outline-none focus:ring-2 focus:ring-volt/40",
        props.className,
      )}
    />
  );
}

export function Select({ children, ...props }) {
  return (
    <select
      {...props}
      className={cn(
        "w-full rounded-[12px] border border-line bg-bone px-3 py-2.5 text-sm text-ink",
        "focus:border-volt-press focus:outline-none focus:ring-2 focus:ring-volt/40",
        props.className,
      )}
    >
      {children}
    </select>
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-2 text-ink-soft">
      <Loader2 className="size-4 animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

/** A circular progress ring (calories/protein/etc). value/max → arc; volt when full. */
export function StatRing({ value, max, label, unit, size = 132 }) {
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const full = pct >= 0.999;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-line)" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={full ? "var(--color-volt-press)" : "var(--color-teal)"}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - pct)}
            style={{ transition: "stroke-dashoffset .7s cubic-bezier(.2,.8,.2,1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="stat-number text-2xl">{Math.round(value)}</span>
          {unit && <span className="text-xs text-ink-soft">{unit}</span>}
        </div>
      </div>
      <span className="text-sm font-medium text-ink-soft">{label}</span>
    </div>
  );
}
