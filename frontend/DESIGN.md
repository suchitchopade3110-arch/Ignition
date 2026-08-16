# Ignition — Frontend Design Spec

Redesign mode: **preserve**. Existing brand tokens (dark base, orange accent) are kept as-is;
this document tightens the system around them, it does not replace them.

Design read: dashboard/app product for engineering teams and CTOs (trust-first B2B, technical
audience) with a marketing site in front of it, in a dark-tech visual language.

Dials: `DESIGN_VARIANCE 6` / `MOTION_INTENSITY 5` / `VISUAL_DENSITY` landing `3`, dashboard `6-7`.

---

## 1. Visual theme and atmosphere

Preset: **Dark Tech**. Graphite/near-black base, a single signal accent (orange, not the usual
electric-blue/emerald default), hairline low-opacity borders, mono reserved for data. No frosted
glass on working surfaces — this is an app people stare at diffs and findings in, not a media
showcase.

**Morphism decision: flat with hairline depth, not glassmorphism. Resolved and implemented.**
- Glassmorphism is explicitly wrong for dashboards: `backdrop-filter` panels read as decorative
  once the screen is full of diffs and findings, and blur tanks contrast on dense text.
- Default treatment everywhere in the app shell: flat surfaces + hairline borders at low opacity
  + a 1px inset highlight on elevated elements only. No blur, no frosted layers.
- The **one** place glass is allowed: a top nav or a floating command palette/modal backdrop, if
  one gets built. Never on `stats-card`, `finding-card`, sidebar, or any data-bearing surface.
- Neumorphism: not used anywhere. Wrong contrast profile for dark mode, no precedent in the
  current UI, skip it entirely.
- "Double-bezel" premium depth (nested container, 1px inner border, rotated backing plate) stays
  confined to the marketing landing page hero (`hero-section.tsx`, `langgraph-visualization.tsx`),
  where it already exists. Do not let it leak into the authenticated app shell.

---

## 2. Color palette

Brand stays brand — orange accent is the redesign-preserve override and is not renegotiable.
Five roles total (background / surface / border / accent / status), no second accent anywhere.

| Token | Value | Status | Role |
|---|---|---|---|
| `--color-background` | `#09090B` | keep | app background |
| `--color-card` | `#18181B` | keep | resting surface |
| `--color-elevated` | `#202024` | **add** | modals, popovers, dropdowns — currently identical to `card`/`popover`, so nothing visually lifts off the page. New step needed. |
| `--color-secondary` | `#27272A` | keep | chips, secondary buttons |
| `--color-border` | `#3F3F46` | keep | card edges, primary dividers |
| `--color-border-subtle` | `#2A2A30` | **add** | internal dividers (table rows) — everything currently uses one border weight, flattening hierarchy |
| `--color-primary` | `#FF4500` | keep | brand, primary CTA, links, focus ring |
| `--color-success` | `#10B981` | keep | ACS score up, passing checks |
| `--color-warning` | `#F59E0B` | keep | medium-severity findings |
| `--color-critical` | `#DC2626` | keep | critical-severity findings only |
| `--color-destructive` | `#EF4444` | **rename from `danger`** | destructive actions (reject, delete) — was a literal duplicate of `destructive`; collapse the two names so severity (`critical`) and action (`destructive`) stop visually colliding |
| `--color-info` | `#3B82F6` | keep | informational states, running/queued status |

Rule going forward: saturation stays under 80%, one accent max, no gradient gets added to any
component beyond the two already in the hero (headline gradient, glow-shadow CTA). Don't let
gradients spread into dashboard chrome.

### Landing two-tone scale

The marketing page alternates dark and warm-cream grounds. This is deliberate and is kept as a
distinct named scale rather than being flattened into the application tokens above.

| Token | Value | Role |
|---|---|---|
| `--color-surface-dark` | `#090A0B` | dark section ground |
| `--color-surface-dark-raised` | `#0E1012` | first lift off the ground |
| `--color-surface-dark-panel` | `#121416` | panel fill |
| `--color-surface-dark-elevated` | `#191C1F` | elevated panel fill |
| `--color-surface-dark-border` | `#202326` | hairline |
| `--color-surface-dark-border-strong` | `#292D31` | emphasised hairline |
| `--color-surface-dark-fg` | `#F4F3EF` | text on dark |
| `--color-surface-dark-muted` | `#9A9C9F` | secondary text on dark |
| `--color-surface-light` | `#F1EFE9` | cream section ground |
| `--color-surface-light-border` | `#D6D3C9` | hairline on cream |
| `--color-surface-light-fg` | `#17191B` | text on cream |
| `--color-surface-light-muted` | `#5F6265` | secondary text on cream |

`--color-primary-hover` (`#FF6A1A`) is the single hover variant of the brand accent.

**No raw hex in components.** Every colour goes through a token. The landing page previously
carried 259 hardcoded hex literals and two competing brand oranges; that is the failure mode
this scale exists to prevent.

---

## 3. Typography

Inter stays as the body/UI face — it's a legitimate utility choice for a data-dense app, not a
slop tell on its own (it only reads as a tell when paired with the AI-purple-gradient default
cluster, which this app does not use).

Additions:

- **Tabular-numerals mono face** (JetBrains Mono or IBM Plex Mono) for ACS scores, commit SHAs,
  PR numbers, diff-viewer line numbers, and timestamps. Today these are set in Inter, which makes
  score columns and metrics wobble instead of aligning — mono is a semantic choice here, reserved
  for identifiers and metrics, not decoration.
- **Explicit shared scale**, replacing today's ad-hoc per-component sizing (`text-5xl` /
  `text-6xl` / `text-7xl` hardcoded in the hero and nowhere else):
  - `text-display` — landing hero headline only
  - `text-h1` / `text-h2` — page and section titles, shared between landing and dashboard
  - `text-body` — default copy
  - `text-caption` — metadata, timestamps, helper text
- Tight, deliberate tracking on display sizes only; body text keeps default tracking.

---

## 4. Component stylings

- **Cards** (`finding-card`, `stats-card`, repo cards): flat `--color-card` fill, `--color-border`
  edge, no shadow beyond a 1px inset highlight. No drop shadows.
- **Severity badges**: solid-fill pill using the exact status color, never the destructive color —
  keeps "this finding is critical" visually distinct from "this button deletes something."
  Reference: `severity-badge.tsx`.
- **Tables** (`table.tsx`): use `--color-border-subtle` for row dividers, full `--color-border`
  only on the outer container edge.
  - Below `sm:` breakpoint, collapse to stacked cards rather than horizontal-scrolling the table.
- **Modals/popovers/dropdowns**: promote to `--color-elevated`, not `--color-card`, so they read
  as lifted above the page they're layered on.
- **Diff viewer / markdown preview**: wide content gets its own `overflow-x: auto` container,
  never page-level horizontal scroll.
- **Sidebar / app shell**: on mobile, collapses to a drawer, not a squeezed fixed column.
- **Buttons**: primary retains the existing glow-shadow treatment (`shadow-[0_0_20px_rgba(255,69,0,0.3)]`)
  on the landing page only; inside the authenticated app shell, primary buttons stay flat — the
  glow is a marketing-page signature move, not a system-wide default.

---

## 5. Layout principles

- Landing page: asymmetric hero (already correct), avoid three-equal-cards anywhere in
  `feature-grid.tsx` — use a 2-column zigzag (max 2 consecutive) or asymmetric bento instead.
- Dashboard: grid-based, `VISUAL_DENSITY 6-7` — this is the one context in the whole product where
  a denser, more instrument-panel layout is correct, because the audience is scanning metrics and
  findings, not reading a magazine.
- Consistent max-width container across dashboard pages; no flexbox-percentage math for page grids.
- Vertical rhythm: section spacing on the landing page should vary on purpose, not repeat one
  fixed padding value down the whole page.

---

## 6. Responsive rules

- Strict single column below 768px for any section carrying `DESIGN_VARIANCE` above 4 (the hero,
  the bento sections on the landing page).
- Sidebar becomes a drawer below `md:`.
- Tables become stacked cards below `sm:`.
- Tap targets stay at or above 44px in dashboard controls (HITL approve/reject, table row actions).
- Diff viewer and markdown preview scroll horizontally inside their own container, never the page.

---

## 7. Motion philosophy

Existing framer-motion usage (staggered hero entrance, spring easing) is already purposeful —
extend the same spring easing to dashboard state transitions instead of adding new motion
elsewhere:

- SSE-driven UI updates (a finding appearing, an agent status flipping to `completed`) should use
  the same spring transition as the hero, not an instant pop-in.
- Hover/focus/press states on every interactive dashboard element — currently only the marketing
  page has rich hover states; the app shell needs the same baseline (weight/opacity shift on
  hover, visible focus ring using `--color-primary`).
- Respect `prefers-reduced-motion`: fall back to opacity-only transitions, no translate/scale.

---

## 8. Anti-pattern list (do not reintroduce)

- No glassmorphism on any data-bearing surface (findings, stats, tables, sidebar).
- No neumorphism anywhere.
- No second accent color; no gradient outside the two existing hero uses.
- No three-equal-cards feature rows.
- No em dash or en dash used as a separator anywhere in UI copy.
- No more than one eyebrow (uppercase, wide-tracking label) per three landing sections.
- No fake product UI built from styled divs — every dashboard mock or screenshot must be the real
  component, not a decorative stand-in.
- No duplicate color tokens (the `danger`/`destructive` collision above is the one to fix first).
- No card-in-card-in-card nesting.

---

## 9. Status

Done:

- Auth guard on protected routes, per-route loading and error boundaries, focus-visible rings.
- `--color-elevated`, `--color-border-subtle`; the `danger`/`destructive` duplicate is collapsed.
- Tabular mono face (JetBrains Mono) wired up for identifiers and metrics.
- Landing two-tone palette promoted to tokens; single brand orange across the codebase.
- Dead landing components removed; the footer is restored and on the page.
- Heading outline is h1 -> h2 -> h3 with no skipped levels.
- Skip-to-content link; `prefers-reduced-motion` honoured by framer-motion and CSS;
  `prefers-reduced-transparency` fallback for every glass surface.
- Capabilities section rebuilt on an asymmetric 7/5 grid.
- Dashboard loading, error and empty states scoped per panel.
- Fabricated trend percentages removed from the dashboard.
- Shared heading scale (`text-display` / `text-h1` / `text-h2` / `text-h3`) implemented as
  Tailwind v4 theme tokens. Landing sizes are fluid via `clamp()`, replacing what used to be
  three stacked breakpoint variants per heading. Applied to every h1/h2/h3 on the landing page
  and to `PageHeader`'s app-shell h1. This also unified the two h3 sizes that previously
  disagreed (`text-base` vs `text-lg`) and the outlier final-CTA h2 that was larger than the
  other four section headers for no stated reason.

- Glass removed from every data-bearing surface (stats cards, finding cards, dashboard panels,
  the reviews table, HITL cards, ledger cards and skeletons, repo cards): `bg-card/60
  backdrop-blur-md` -> `bg-card`, 19 call sites across 7 files. Glass stays where the spec always
  allowed it: the top nav, the sidebar, the mobile drawer overlay, the settings dialog, the user
  menu dropdown, and the single login card.

- Glass CSS consolidated: `.glass-header`, `.glass-sidebar`, `.glass-panel-elevated` now applied
  at the four sites that were hand-rolling the identical value inline (app-shell header and
  sidebar wrapper, the settings dialog, the user menu dropdown). Found and fixed a real bug along
  the way — the desktop sidebar was compositing two stacked blur layers for one visible edge.
  Added `.glass-scrim` for the modal/drawer dimming backdrop, previously duplicated verbatim in
  two places.
- Footer no longer links Terms/Privacy/Security/Pricing/Changelog/Status to the wrong destination.
  They render as inert "Soon" text instead of live navigation to `/login` or `/dashboard`.
- SSE-driven agent status changes and finding arrivals now animate (crossfade / opacity+y entrance)
  instead of popping in instantly, riding the existing `MotionConfig reducedMotion="user"` provider.
- Caption-scale consolidated. Added `--text-caption` (11px) and replaced `text-[10px]` /
  `text-[11px]` at 19 sites across 9 real-app files (dashboard, HITL, ledger, repos, reviews,
  `agent-timeline`, `finding-card`, `diff-viewer`, `user-menu`). Several were the same element at
  two different sizes purely from desktop-table vs mobile-card duplication, with no reason for the
  split. Verified with live overflow measurement (`scrollWidth` vs `clientWidth`) at 1000px and
  375px on every site, including the diff-viewer's fixed 40px gutter — the highest-risk one.
  Deliberately excluded: `hero-product-console.tsx` (a self-contained decorative landing mockup
  with its own intentional 9/10/11px density hierarchy) and the footer's one-off "Soon" badge.
- Footer's six placeholder links now go to real pages (`/pricing`, `/changelog`, `/security`,
  `/privacy`, `/terms`, `/status`), replacing the inert "Soon" text. Pages are an honest "not live
  yet" shell (`ComingSoonPage`), not fabricated legal/policy content — inventing real-looking Terms
  of Service or Privacy Policy text would be actively misleading, not just incomplete.
- Dashboard trend indicator restored with real data. `ReviewRepository._issues_found_trend()`
  compares this week's vs last week's `sum(findings_count)`; returns `None` (not a fabricated 0%)
  when there's no prior-week baseline. Deliberately not added to `active_reviews`, since that's an
  instantaneous snapshot, not a metric a week-over-week percentage would honestly describe.

Outstanding: none currently tracked.
