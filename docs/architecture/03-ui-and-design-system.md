# Dentiva Pro — UI Architecture and Clinical Design System (Phase 1)

Toolkit: **PySide6 / QtWidgets**. All styling comes from one token source; no screen defines its own
colours, spacing or fonts. Everything below is implemented in `src/dentivapro/ui/design/` and consumed
by `ui/components/` and `ui/screens/`.

---

## 1. Design language

**Clinical premium, not decorative.** Deep slate ink on a soft neutral canvas, one restrained teal
accent, semantic colours reserved for clinical/financial meaning, generous but disciplined spacing,
tables that read like a medical chart, and motion that only ever clarifies.

Principles: clarity over ornament · quiet confidence over gradients · density where clinicians need it
(tables, charts, odontogram) and air where decisions happen (registration, prescription, payment) ·
colour carries meaning, never decoration · every state is designed (empty, loading, error, denied,
disabled, selected, dirty, saved).

---

## 2. Design tokens (`ui/design/tokens.py`)

### 2.1 Colour

| Token | Value | Use |
|---|---|---|
| `ink.900 / 800 / 700` | `#0B1220 / #1b2436 / #334155` | Headings, primary text, secondary text |
| `ink.600 / 500 / 400` | `#475569 / #64748B / #94A3B8` | Muted text, placeholders, disabled |
| `surface.base` | `#F6F8FA` | App canvas |
| `surface.raised` | `#FFFFFF` | Cards, tables, dialogs |
| `surface.sunken` | `#EEF2F6` | Table headers, wells, inactive tabs |
| `border.subtle / strong` | `#E2E8F0 / #CBD5E1` | Hairlines, dividers, input borders |
| `accent.600 / 500 / 100 / 050` | `#0F766E / #0D9488 / #CCFBF1 / #ECFDF5` | Primary actions, focus, selection |
| `accent.ink` | `#0B5F59` | Accent text on light accent fill (contrast ≥ 4.5:1) |
| `info / success / warning / danger` (`-fg`, `-bg`, `-border`) | `#0369A1/#065F46/#B45309/#B91C1C` families | Status badges, alerts, validation |
| `data.1…6` | Teal, slate, amber, violet, cyan, rose (colour-blind-safe ordering) | Charts |
| `tooth.<condition>` | Per-condition colours, contrast-checked, also distinguished by pattern/label | Odontogram |

Rules: text on `surface.raised` ≥ 4.5:1 contrast; status is never communicated by colour alone (icon or
label always accompanies); a light/dark audit of every screen is part of the UI review checklist.

### 2.2 Typography

Families: `Inter` (Latin/UI), `Noto Sans Bengali` (Bangla), fallback chain
`Inter → Noto Sans Bengali → Segoe UI → system`, monospace `Cascadia Mono → Consolas` for codes/amounts.
Bundled fonts guarantee identical rendering on every machine (also the basis of deterministic visual tests).

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `display` | 28 / 36 | 700 | Rare, e.g. setup wizard step titles |
| `h1` | 22 / 30 | 700 | Screen titles |
| `h2` | 18 / 26 | 600 | Section headers |
| `h3` | 15 / 22 | 600 | Card titles, dialog titles |
| `body` | 13.5 / 20 | 400 | Default UI text |
| `body.strong` | 13.5 / 20 | 600 | Emphasis inside body |
| `label` | 12.5 / 18 | 600 | Form labels, table headers (with 0.02 em tracking) |
| `caption` | 11.5 / 16 | 400 | Helper text, timestamps, meta |
| `mono` | 13 / 20 | 500 tabular figures | Codes, amounts, reference numbers |
| `amount.lg` | 20 / 28 | 700 tabular figures | Invoice totals, KPI values |

Bengali text automatically uses ≥ 1px larger effective size and ≥ 1.15 line-height
(`ui/design/text.py::BengaliAwareLabel`) because Bengali glyph height differs; this is applied
centrally, never per screen.

### 2.3 Spacing, radii, borders, elevation

- Spacing scale (px): `2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48`. Default gutters: screen 24,
  card internal 20, form row 16, table cell 12/8, button padding 16/9.
- Radii: `sm 6`, `md 8`, `lg 10`, `pill 999`. Inputs/buttons 8, cards 10, badges pill.
- Borders: `1px @ border.subtle` for cards/dividers, `1px @ border.strong` for inputs,
  `2px @ accent.500` focus ring + `1px` offset.
- Elevation: `e0` flat (tables), `e1` card (1px 2px rgba(15,23,42,.06)), `e2` popover/dropdown,
  `e3` dialog/drawer (`0 10px 30px rgba(15,23,42,.14)`), `e4` lock layer scrim.

### 2.4 Motion

Durations `fast 120 ms`, `base 160 ms`, `slow 240 ms`; easing `ease-out-cubic` (Qt `QEasingCurve.OutCubic`).
Permitted: hover/focus colour transitions, card lift on interactive cards, dialog fade+8 px rise,
drawer/slide-over 200 ms, toast slide-in, skeleton shimmer, progress bar easing, number tick-up on KPI
values (≤ 400 ms, and disabled when the user enables *Reduce motion*).
Forbidden: parallax, looping decorative animation, anything > 300 ms on a data path, blocking animations
on save/print, animation of table rows.

### 2.5 Sizing, metrics and density

| Token | Value |
|---|---|
| Control heights | `xs 26` (table inline), `sm 30` (toolbar), `md 34` (default buttons/inputs), `lg 40` (wizard primary) |
| Table row height | comfortable `40`, compact `32` (user-selectable, persisted per screen) |
| Icon sizes | `12, 14, 16, 18, 20, 24, 32, 48` with 16 default; icons are vector and snapped to the pixel grid |
| Sidebar widths | expanded `248`, collapsed `72` |
| Header height | `60` |
| Content max width | none for tables; forms constrained to `760` (single column) / `1120` (two column) for readability |
| Dialog sizes | `sm 420×auto`, `md 560×auto`, `lg 760×(≤ 80 % viewport)`, `xl 1000×(≤ 85 % viewport)`; every dialog scrolls internally and can never exceed the viewport |
| Toast | width `380`, auto-dismiss `4 s` (errors `8 s`, dismissible) |

### 2.6 Responsive desktop rules (viewport, not device)

| Viewport width | Behaviour |
|---|---|
| ≥ 1600 | Sidebar expanded, 4-column KPI grid, tables show all configured columns |
| 1280–1599 | Sidebar expanded, 4→3-column KPI grid, secondary table columns hidden with a "columns" menu |
| 1024–1279 | Sidebar auto-collapses to icons (user can pin it), 2-column KPI grid, patient profile switches to stacked tabs |
| < 1024 | Sidebar overlay mode, 1–2-column grids, detail panels become full-width drawers, odontogram switches to quadrant focus mode with horizontal scroll |

Windows-specific realities handled: 125/150/175/200 % scaling, 1366×768 laptops, 2560×1440 and
3440×1440 ultrawides, vertical taskbar reducing usable height, and multi-monitor moves (the app
re-clamps dialogs into the visible screen area).

---

## 3. Application shell

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] Dentiva Pro   │  Sunrise Dental Care · Dhanmondi, Dhaka  │ Wed, 01 Oct 2026  │
│                                                            🔍  🔔(3)  ⓘ  👤 Dr. Shohan Khan │
├───────────────┬──────────────────────────────────────────────────────────────────────┤
│ PRACTICE      │  Screen title                        context actions / filters       │
│  Dashboard    │  ─────────────────────────────────────────────────────────────────── │
│  Patients     │                                                                      │
│  Appointments │            content region (cards, tables, forms, charts)             │
│  Queue        │                                                                      │
│ CLINICAL      │                                                                      │
│  Treatments   │                                                                      │
│  Prescriptions│                                                                      │
│ BILLING       │                                                                      │
│  Invoice      │                                                                      │
│  Payments     │                                                                      │
│  Inventory    │                                                                      │
│  Accounting   │                                                                      │
│ ADMINISTRATION│                                                                      │
│  Staff & Users│                                                                      │
│  Backup       │                                                                      │
│  Settings     │                                                                      │
│  About        │                                                                      │
│ ‹collapse     │                                                                      │
└───────────────┴──────────────────────────────────────────────────────────────────────┘
```

- **Header:** product identity, clinic identity (name + city, from settings), live date & clinic clock,
  global search (focused with `Ctrl+K`), notification centre with unread badge, help/`ⓘ` diagnostics
  menu, and the user chip (name, role, dentist link) with session menu (Lock now, Switch user, Logout).
- **Sidebar:** the four required areas exactly as specified, collapsible (`Ctrl+B`), with permission-aware
  visibility, active-route indicator, quiet section labels, and a footer that shows app version + build.
  Additional professional modules appear inside the matching area (e.g. *Referrals* under Clinical,
  *Reports* under Billing, *Audit log* under Administration) without removing any required entry.
- **Routing:** a small router (`ui/shell/router.py`) maps routes to screen factories, supports deep links
  (`patient/123/visit/45`), back/forward (`Alt+←/→`), and restores the last route + scroll position per
  user. Every route declares its required permission; the router refuses unauthorised routes and renders
  a proper "permission denied" screen (never a blank page).
- **Notifications:** one central `NotificationCenter` service; the header bell shows an unread count,
  the panel lists gated items (a notification carries `required_permission`), and severity icons/tints
  match the token system. Sources: upcoming/missed appointments, low stock, near-expiry, backup
  success/failure, restore results, security events, outstanding operational issues. Deduplicated by
  `dedupe_key` so the centre never becomes noise.

---

## 4. Component inventory (`ui/components/`)

**Primitives:** `Button` (primary/secondary/ghost/danger/icon, sizes xs–lg, loading and disabled states),
`IconButton`, `ButtonGroup` (segmented), `TextField`+`TextArea` (label, helper, error, optional Bengali
input hint, character counter), `SearchField` (debounced, clearable), `ComboBox`, `MultiSelect`,
`DateField` (calendar popup, keyboard entry, "today" shortcut), `TimeField`, `DurationField`,
`NumberField` (decimal-safe, thousands separators, BDT adornment), `MoneyField` (৳ prefix,
paise handling), `PhoneField` (BD format `+8801XXXXXXXXX` / `01XXXXXXXXX` normalisation), `Toggle`,
`Checkbox`, `RadioGroup`, `TagInput`, `AttachmentDropZone`.

**Structure:** `Card` (+`CardHeader`, `CardBody`, `CardFooter`, `KpiCard`), `SectionHeader`, `Tabs`
(underline style, scrollable when many), `Accordion`, `Drawer` (right side, 420/560 width, ESC-closable,
focus-trapped), `Dialog` (+`ConfirmDialog`, `DestructiveConfirmDialog` requiring a typed phrase),
`Stepper` (wizard), `Breadcrumb`, `Divider`, `EmptyState` (icon, title, explanation, primary action),
`LoadingState` (skeleton rows/panels, no spinner-only screens), `ErrorState` (message + retry +
diagnostic id), `PermissionDeniedState`, `OfflineNotice` (informational: "works fully offline").

**Data:** `DataTable` (sticky header, sortable columns, per-column alignment/format, row density toggle,
column chooser, keyboard navigation, copy cell, row actions menu, inline status badges, selection model,
empty/loading/error overlays, sticky summary footer for totals, virtualised model for large sets),
`Pagination`/`LoadMore` (keyset), `FilterBar` (date range presets Today/7/30/90/1y/Custom, saved
filters), `TimelineView` (patient longitudinal history), `StatTile`, `StatusBadge`, `ProgressBar`,
`SparkLine`, `BarChart`, `LineChart`, `DonutChart`, `HeatStrip` (yearly activity), all hand-painted with
`QPainter` on tokens (no external charting dependency, deterministic output, no licence risk).

**Clinical:** `Odontogram` (adult permanent FDI 11–48 and pediatric primary 51–85, click/drag selection,
multi-tooth selection, per-tooth condition menu, quadrant/arch grouping, colour + pattern + label coding,
zoom, side legend, quadrant-focus mode on narrow viewports, keyboard navigation with arrow keys and
`Space` to apply the active condition, tooltip with the patient's history for that tooth),
`FindingPicker` (categorised chips for C/C, O/E, Dx, advice with search and free-text add),
`MedicineRow` (formulation, strength, dose grid morning/noon/night, food relation, duration, quantity,
instructions, reorder handles, duplicate/copy actions), `ToothSelector` (chips for the teeth attached to
a treatment), `VisitSummaryCard`, `PrescriptionPreview`, `InvoicePreview`, `PrintPreviewPanel`.

**Feedback:** `Toast` (stack bottom-right, severity, action link, queue-limited), `InlineBanner`,
`ConfirmBar` (unsaved changes), `BusyOverlay` (with cancel for long operations), `FieldError`.

Every component is implemented once, used everywhere, has a documented keyboard contract and a golden
image test at 100 %, 150 % and 200 % scaling.

---

## 5. State design per screen (mandatory)

| State | Requirement |
|---|---|
| Loading | Skeleton that matches the final layout; never a blank panel; operations > 400 ms show progress; > 2 s show an estimated action plus cancel where safe |
| Empty | Explained in clinic language with a primary action; distinguishes "no data yet" from "no results for this filter" (with a *clear filter* action) |
| Error | Human message, retry action, expandable technical detail (redacted), correlation id |
| Permission denied | Professional explanation, the permission needed, and a hint to contact the administrator; never a redirect to a blank screen |
| Validation | Field-level inline errors + a summary at the top of long forms; first invalid field focused on save |
| Dirty form | Guard on navigation/close with Save / Discard / Stay; no accidental data loss |
| Success | Toast + obvious persisted state (row appears, badge updates, totals refresh) |
| Disabled | Visually distinct, with a tooltip explaining *why* (e.g. "Requires 'Invoice finalize' permission") |
| Long content | Ellipsis with full-value tooltip, wrap where appropriate, never clipped; tables scroll horizontally with sticky first column (patient name) |

---

## 6. Keyboard contract

| Shortcut | Action |
|---|---|
| `Ctrl+K` | Global search (patients, appointments, visits, prescriptions, invoices, payments, inventory, staff — permission-filtered) |
| `Ctrl+N` | New in current context (patient, appointment, visit, invoice, prescription — route-aware) |
| `Ctrl+Shift+P` | New patient (global) |
| `Ctrl+S` | Save current form (disabled when nothing to save) |
| `Ctrl+P` | Print preview for the active document |
| `Ctrl+B` | Toggle sidebar |
| `F5` | Refresh current screen |
| `Ctrl+1…9` | Jump to the first nine navigation entries |
| `Alt+←/→` | Back / forward |
| `Esc` | Close dialog/drawer (respecting unsaved-changes guard) |
| `F1` | Context help / About |
| `Ctrl+L` | Lock now |
| `Tab`/`Shift+Tab`/arrows/`Space`/`Enter` | Standard Windows focus traversal; tables fully keyboard navigable; odontogram navigable with arrows + `Space` |

No shortcut overrides standard Windows behaviour (e.g. `Alt+F4`, `Win+*` remain untouched), and every
shortcut is discoverable through tooltips and a searchable in-app shortcut reference.

---

## 7. Export, print and clipboard rules

- Lists/reports export to **CSV (UTF-8 with BOM for Excel Bengali support)** and **PDF**; exports honour
  the same permission gate and are audited; the file path is chosen through the native save dialog.
- Print preview is available for prescriptions, invoices, and reports, with printer selection, paper
  profile selection, copies and page range; failures explain the cause in plain language.
- Clipboard operations copy the ledger-ready value (e.g. `৳ 12,450.75` with a settings-driven format).

---

## 8. Accessibility and comfort

- Contrast: WCAG AA for text and essential UI; status never by colour alone.
- Full keyboard operation for every workflow, visible focus, logical tab order, no focus traps.
- Targets ≥ 24×24 px for pointer actions.
- *Reduce motion* setting disables non-essential animation; no flashing content.
- Screen-reader names/descriptions set on interactive widgets (Qt accessibility API).
- Numeric entry accepts Bengali or ASCII digits and normalises on commit.

---

## 9. UI defect checklist (executed per phase and in Phases 17 and 18)

1. Every label visible and untruncated at 100–200 % DPI, including long Bengali strings.
2. Every icon optically centred in its button at each icon size.
3. Buttons: none with clipped/inaccessible text; primary actions distinguishable from secondary.
4. Tabs clickable, keyboard reachable, with correct active state and no unreachable overflow.
5. Scroll containers actually scroll; no nested scroll traps; sticky headers behave.
6. Tables: long text (500-char medicine names, long addresses), 20+ columns, 50 k rows, horizontal
   scrolling, per-column alignment, totals row, no row-height jumping.
7. Modals fit the smallest supported viewport (1024×640) and scroll internally.
8. Forms: validation, required indicators, focus on first error, dirty-state guard.
9. Overlap/escape checks: nothing outside its container; no clipped dropdowns near screen edges
   (popups flip and clamp); drawers and toasts do not cover primary actions.
10. Consistent spacing/radii/colour — verified by review plus a token-lint test that fails the build if a
    screen file contains raw hex colours, hard-coded pixel paddings or inline font sizes.
11. Empty/loading/error/denied states present on every data screen (automated route checklist test).
12. High-DPI: 100/125/150/175/200 % golden renders reviewed for blur, clipping or misalignment.
13. Realistic-content passes: long names, long addresses, multiple qualifications, many medicines,
    Bengali text, large amounts, empty optional values, very long single words, 100+ row lists.

---

## 10. Automated UI verification

- **Golden image tests** (`tests/ui/`): each screen and key component is rendered offscreen at multiple
  DPIs with deterministic fixtures (seeded data, bundled fonts, `QT_QPA_PLATFORM=offscreen`) and compared
  against committed goldens with a small perceptual tolerance; intentional changes regenerate goldens via
  a documented command. Windows-produced goldens are authoritative because the product is Windows-first.
- **Interaction tests** (`pytest-qt`): keyboard traversal, dialog open/close, validation feedback,
  permission-driven visibility *and* service refusal, unsaved-changes guard, table sorting/filtering,
  pagination, toast lifecycle, lock/unlock, and print-preview invocation (with a mock print engine so CI
  needs no printer).
- **Layout invariants test**: at four viewport sizes and five DPI settings, asserts no widget geometry
  exceeds its parent, no text elides without an ellipsis marker, and no dialog exceeds the screen.
- These tests are the reason the design system is token-driven and hand-painted: the output is
  deterministic and reviewable in CI on Windows.
