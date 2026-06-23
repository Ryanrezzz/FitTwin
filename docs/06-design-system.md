# 06 · Design System — "Athletic Performance"

> The brief: **must not look like every other AI app.** No dark-purple/indigo gradient, no glowing-orb-on-black.
> FitTwin should feel like a **premium sports-performance product** — think a flagship running-shoe site or an
> elite gym app — *energetic, physical, confident, fresh.*

---

## 1. Design principles

1. **Physical, not digital-mystical.** Motion implies *effort and momentum* (springs, weight, snap) — not the
   slow ethereal float of AI marketing sites.
2. **Light-first, high-contrast.** A bright, clean canvas with one electric accent reads as "fitness/energy,"
   the opposite of the dark-AI cliché. (A true-dark "night gym" mode exists, but it's charcoal+volt, never purple.)
3. **Data is the hero.** Big confident numbers, rings, and charts. The UI celebrates *your* metrics.
4. **One signature object:** the **3D Digital Twin** — the thing people screenshot.
5. **Accessibility is non-negotiable:** AA contrast, full `prefers-reduced-motion` support, keyboard paths.

---

## 2. Color system (no purple — anywhere)

Energetic, athletic, fresh. **Volt-green** is the brand spark (high-energy, unmistakably "sport"), grounded by
near-black ink on a warm bone canvas, with coral for streaks/heat and teal for calm data.

```css
/* styles/tokens.css — light (default) */
:root {
  --bone:        #F6F5F0;   /* warm off-white canvas (NOT pure white) */
  --paper:       #FFFFFF;   /* card surface */
  --ink:         #0E0F0C;   /* near-black text */
  --ink-soft:    #4B4E45;   /* secondary text */

  --volt:        #C6F833;   /* PRIMARY — electric lime/volt, the energy accent */
  --volt-press:  #A9DC1F;   /* pressed/active */
  --coral:       #FF6B4A;   /* streaks, heat, "push" moments */
  --teal:        #15B8A6;   /* calm data / charts / success */
  --amber:       #F5A524;   /* warnings (Safety agent), warm not alarming */

  --line:        #E7E5DD;   /* hairline borders */
  --radius:      16px;      /* generous, soft-athletic */
  --shadow:      0 1px 2px rgba(14,15,12,.06), 0 8px 24px rgba(14,15,12,.06);
}

/* "Night Gym" dark mode — charcoal + volt, deliberately NOT purple */
[data-theme="dark"] {
  --bone:  #121310;  --paper: #1A1C18;  --ink: #F3F4EE;  --ink-soft:#A9ADA0;
  --line:  #2A2D26;  --volt:  #CBFF3E;  /* coral/teal/amber unchanged */
}
```

**Usage rules:** volt is for *action and energy* (primary buttons, the active ring, the Twin's glow) — used
sparingly so it stays electric. Coral = streaks/personal-records/"intensity." Teal = neutral-good data. Amber =
Safety-agent warnings (calm caution, never a harsh red). Charts pull straight from these tokens.

> Want a calmer alternative? A "Wellness" variant (sage `#7FA67E`, terracotta `#C26B4E`, cream) is documented as
> an optional theme — same tokens, different values. Volt-athletic is the recommended default.

---

## 3. Typography — sports-brand pairing

| Role | Font | Why |
|---|---|---|
| **Display / headlines** | **Archivo Expanded** (or *Anton* / *Bebas Neue*) — wide, bold, condensed-athletic | Reads like a sports/performance brand; big metric numbers feel powerful |
| **Body / UI** | **Inter** (or *Geist* / *Satoshi*) | Clean, legible grotesk for data-dense screens |
| **Numerals** | tabular-nums | Charts & stat rings don't jitter as values change |

```css
--font-display: "Archivo", system-ui;     /* wght 800, slightly expanded */
--font-body:    "Inter", system-ui;
/* Huge confident stats: */ .stat { font: 800 clamp(2.5rem,6vw,4.5rem)/0.95 var(--font-display); letter-spacing:-0.02em; }
```

---

## 4. Motion language (Framer Motion)

Motion = **physical momentum**. Spring-based, with weight; quick and snappy, never the dreamy AI float.

```ts
// components/motion/presets.ts
export const spring = { type: "spring", stiffness: 420, damping: 32, mass: 0.9 };
export const fadeUp = {
  initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 },
  transition: spring,
};
export const stagger = { animate: { transition: { staggerChildren: 0.06 } } };
```

**Signature interactions**
- **CountUp stats** — numbers spring-count to value on mount (`useMotionValue` + `animate`).
- **Stat rings fill** — animated `pathLength` (calories/protein/steps), volt when complete.
- **Page transitions** — content slides+settles with `spring` via `AnimatePresence`.
- **Streak flame** — coral particle pop when a streak increments.
- **Chat agent-steps** — each agent chip drops in with `stagger` as the orchestrator routes ("🔎 Progress →
  🥗 Nutrition → 🏋️ Workout → 🛡️ Safety").
- **`MotionConfig reducedMotion="user"`** wraps the app → everything degrades to instant for users who opt out.

> Note on "Remotion": Remotion renders **video**, not in-app UI. So in-app motion = **Framer Motion**; Remotion is
> used for the *feature* below.

---

## 5. The 3D Digital Twin (React Three Fiber)

The hook that makes FitTwin *FitTwin*. A stylized 3D figure on the Dashboard that **reflects your state**:

- **Energy ring / aura** intensity scales with today's goal completion (volt glow grows as you hit targets).
- **Posture/pose** nods to your goal (cut / recomposition / strength).
- **Idle micro-animation** (breathing, slow turn) via `useFrame`; reacts on data update (a satisfied bounce when
  you log a completed workout).
- Built with **`@react-three/fiber` + `@react-three/drei`** (OrbitControls, Environment, Float, useGLTF).
  Model: a low-poly stylized humanoid GLB, or — to stay light — an abstract "energy core" (icosahedron + animated
  shader/distort material) so it's striking without a heavy asset.

```tsx
// components/three/DigitalTwin.tsx  (lazy-loaded, Suspense-wrapped)
function TwinScene({ energy }: { energy: number }) {  // energy 0..1 = goal completion
  return (
    <Canvas dpr={[1, 1.75]} camera={{ position: [0, 0.5, 4] }} frameloop="demand">
      <Environment preset="city" />
      <Float speed={1.2} rotationIntensity={0.4}>
        <TwinModel />
        <EnergyAura intensity={energy} color="#C6F833" />
      </Float>
      <OrbitControls enablePan={false} enableZoom={false} />
    </Canvas>
  );
}
```

**Performance budget** (3D earns its keep only if it's smooth):
- `frameloop="demand"` (render only on change) + capped `dpr`; pause when tab hidden / off-screen (IntersectionObserver).
- **Lazy chunk** — the whole `three` bundle is `React.lazy` so it never blocks first paint.
- **Reduced-motion / low-power / no-WebGL fallback** → a static volt-gradient hero illustration. The app is fully
  usable without WebGL.

---

## 6. Remotion — shareable weekly recap video

A genuinely differentiating feature *and* the correct use of Remotion. After each weekly review, the backend (or a
serverless render) produces a **15-second motion-graphics recap**: weight delta, calories/protein adherence,
workouts completed, streak, and the coach's headline — animated to a beat, branded in the athletic palette.

- Output: an MP4 the user can download / share to socials → organic growth + a portfolio "wow."
- Implementation: a Remotion composition fed the `WeeklyReport` JSON; rendered headless (`@remotion/renderer`) in
  the worker and stored; served at `GET /progress/recap/{iso_week}.mp4` (V1.5 — see roadmap).

---

## 7. Component & layout conventions

- **shadcn/ui** primitives, **re-skinned to tokens** (volt focus rings, bone surfaces, `--radius`) so it never
  looks like default-shadcn.
- **Bento-grid dashboard** — varied tile sizes (big Twin tile, square stat rings, wide weight chart). Feels modern
  and sporty, not a boring stacked form.
- **Cards**: `--paper` surface, hairline `--line` border, soft `--shadow`, generous radius.
- **Buttons**: primary = volt fill on ink text (high energy); secondary = ink outline; destructive = coral.
- **Empty states** are motivational, not sterile ("Log your first workout to wake up your Twin").
- **Iconography**: `lucide-react`, slightly heavier stroke to match the athletic weight.

---

## 8. Accessibility & theming checklist

- AA contrast verified (volt is used as a *fill behind dark ink*, never as light text on white — it would fail).
- `prefers-reduced-motion` → `MotionConfig` + static 3D fallback + no chart entrance animation.
- `prefers-color-scheme` seeds light/"Night Gym" dark; user override persisted in `uiStore`.
- Full keyboard nav, visible volt focus rings, `aria-live` on streaming chat and CountUp stats.
- Respect `navigator.deviceMemory` / `hardwareConcurrency` to skip 3D on low-end devices.
