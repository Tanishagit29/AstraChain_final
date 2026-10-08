# AstraChain Design System

## 1. Overview & Brand Identity

The **AstraChain AI Control Tower Design System** is engineered for high-density enterprise supply chain operations and AI copilot interactions. Built on a **Modern Minimalist** core with a technical "Night-Vision" aesthetic, it minimizes cognitive load and eye fatigue while delivering crisp visual hierarchy for telemetry, analytics, stock flow, and real-time AI recommendations.

### Core Visual Principles
- **Modern Minimalism:** Clean line work, subtle glass depth, and structured density without extraneous decoration.
- **Night-Vision Dark Mode:** Deep midnight surfaces paired with high-contrast cyan and vibrant risk accents for multi-screen monitoring environments.
- **Glassmorphism & Depth:** Stacked surface layers with backdrop blur and low-opacity cyan glows to represent AI layers without obstructing background context.
- **Technical Precision:** Dual typography combining clean grotesque sans-serif for UI flow with monospace for data values, telemetry, and system metadata.

---

## 2. Color Palette & Tokens

### 2.1 Foundational Surface Palette
| Token Name | Hex Code | Tailwind / Style Class | Description & Usage |
| :--- | :--- | :--- | :--- |
| `background` | `#0F1418` | `bg-background` | Default app dark foundation |
| `body-bg` | `#0B1120` | `bg-[#0B1120]` | Main window canvas background |
| `surface` | `#0F1418` | `bg-surface` | Primary component background |
| `surface-dim` | `#0F1418` | `bg-surface-dim` | Recessed container background |
| `surface-bright` | `#343A3E` | `bg-surface-bright` | High-lighted surface elevation |
| `surface-container-lowest`| `#0A0F12` | `bg-surface-container-lowest` | Deepest recessed panel layer |
| `surface-container-low` | `#171C20` | `bg-surface-container-low` | Subtle dark card background |
| `surface-container` | `#1B2024` | `bg-surface-container` | Standard container surface |
| `surface-container-high` | `#252B2E` | `bg-surface-container-high` | Elevated interactive controls |
| `surface-container-highest`| `#303539` | `bg-surface-container-highest`| Top-level modal/dropdown layer |
| `glass-card` | `#111C2E` | `bg-[#111C2E]` | Glassmorphic card surface |

### 2.2 Accent & Brand Colors
| Token Name | Hex Code | Tailwind / Style Class | Description & Usage |
| :--- | :--- | :--- | :--- |
| `primary` | `#8ED5FF` | `text-primary`, `bg-primary` | Primary cyan highlight & interactive text |
| `primary-container` | `#38BDF8` | `bg-primary-container` | Main active cyan accent & key action fills |
| `on-primary` | `#00354A` | `text-on-primary` | Dark text rendered on cyan buttons |
| `on-primary-container` | `#004965` | `text-on-primary-container` | Dark contrast text for primary containers |
| `inverse-primary` | `#00668A` | `text-inverse-primary` | High-contrast secondary cyan state |

### 2.3 Secondary & Tertiary Accents
| Token Name | Hex Code | Tailwind / Style Class | Description & Usage |
| :--- | :--- | :--- | :--- |
| `secondary` | `#BDC2FF` | `text-secondary`, `bg-secondary` | Indigo accent for historical trends & secondary elements |
| `secondary-container` | `#2F3AA3` | `bg-secondary-container` | Active navigation pill background |
| `on-secondary` | `#131E8C` | `text-on-secondary` | Deep contrast text on secondary container |
| `on-secondary-container`| `#A8AFFF` | `text-on-secondary-container`| Soft indigo text for active nav items |
| `tertiary` | `#FFC176` | `text-tertiary` | Amber accent for warnings & overstock alerts |
| `tertiary-container` | `#F1A02B` | `bg-tertiary-container` | Highlight background for stock warnings |
| `on-tertiary` | `#472A00` | `text-on-tertiary` | Contrast text on amber containers |
| `on-tertiary-container` | `#613B00` | `text-on-tertiary-container` | Deep amber text |

### 2.4 Semantic & Risk Colors
| Token Name | Hex Code | Tailwind / Style Class | Description & Usage |
| :--- | :--- | :--- | :--- |
| `error` | `#FFB4AB` | `text-error` | Critical stockout risk & urgency text |
| `error-container` | `#93000A` | `bg-error-container` | Background fill for urgent alert badges/buttons |
| `on-error` | `#690005` | `text-on-error` | Contrast text on error fills |
| `on-error-container` | `#FFDAD6` | `text-on-error-container` | Light pink text for critical alerts |
| `near-expiry` | `#FF9800` | `text-[#FF9800]` | Orange warning color for perishable items |

### 2.5 Text & Outline Tokens
| Token Name | Hex Code | Tailwind / Style Class | Description & Usage |
| :--- | :--- | :--- | :--- |
| `on-surface` | `#DEE3E8` | `text-on-surface` | Primary body and heading text |
| `on-surface-variant` | `#BDC8D1` | `text-on-surface-variant` | Secondary labels, descriptions, and icons |
| `outline` | `#87929A` | `border-outline` | Standard outline borders |
| `outline-variant` | `#3E484F` | `border-outline-variant` | Container divider & subtle 1px border lines |
| `border-card` | `#1E293B` | `border-[#1E293B]` | Glass card border stroke |

---

## 3. Typography System

### 3.1 Typeface Families
- **Primary Interface Font:** `Inter`, sans-serif
  - Used for titles, headings, navigation links, body copy, and UI control labels.
- **Technical & Monospace Font:** `JetBrains Mono`, monospace
  - Used for numbers, SKU IDs, table data metrics, telemetry parameters, and timestamp chips.
- **Icon System:** `Material Symbols Outlined`
  - Styled with custom fill parameters (`font-variation-settings: 'FILL' 1;`).

### 3.2 Typography Tokens & Hierarchy
```css
/* Display Large (Hero Headers) */
.font-display-lg {
  font-family: 'Inter', sans-serif;
  font-size: 48px;
  font-weight: 700;
  line-height: 56px;
  letter-spacing: -0.02em;
}

/* Headline Large (Page Titles) */
.font-headline-lg {
  font-family: 'Inter', sans-serif;
  font-size: 32px;
  font-weight: 600;
  line-height: 40px;
  letter-spacing: -0.01em;
}

/* Headline Medium (Card Titles / Section Headers) */
.font-headline-md {
  font-family: 'Inter', sans-serif;
  font-size: 24px;
  font-weight: 600;
  line-height: 32px;
}

/* Title Medium (Modal / Sub-section Titles) */
.font-title-md {
  font-family: 'Inter', sans-serif;
  font-size: 18px;
  font-weight: 600;
  line-height: 24px;
}

/* Body Large (Primary Paragraphs) */
.font-body-lg {
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  font-weight: 400;
  line-height: 24px;
}

/* Body Medium (Standard UI Text) */
.font-body-md {
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 400;
  line-height: 20px;
}

/* Label Medium (Monospace Data Labels) */
.font-label-md {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
  letter-spacing: 0.05em;
}

/* Label Small (Telemetry & Micro Metrics) */
.font-label-sm {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  line-height: 14px;
  letter-spacing: 0.05em;
}
```

---

## 4. Spacing & Layout System

### 4.1 Base 4px Rhythm Scale
| Token | Pixel Value | REM Equivalent | Typical Usage |
| :--- | :--- | :--- | :--- |
| `base` | 4px | 0.25rem | Minimum inline gap, micro padding |
| `xs` | 8px | 0.5rem | Small element gap, icon-to-text spacing |
| `sm` | 12px | 0.75rem | Compact component padding, filter gaps |
| `md` | 16px | 1.0rem | Standard card padding, input field height |
| `lg` | 24px | 1.5rem | Main container padding, section grid gaps |
| `xl` | 32px | 2.0rem | Canvas section margins, top header spacing |
| `2xl` | 48px | 3.0rem | Dashboard section dividers |
| `3xl` | 64px | 4.0rem | Large hero layout spacing |

### 4.2 Layout Grids & Density
- **Main App Shell Layout:** Fixed left sidebar (`280px`) + main content canvas (`md:ml-[280px] min-h-screen`).
- **KPI Summary Grid:** 4-column responsive bento layout (`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-md`).
- **Split Analytics Grid:** 3-column layout (`grid grid-cols-1 lg:grid-cols-3 gap-lg`) where charts occupy `lg:col-span-2` and AI Recommendations occupy 1 column.

---

## 5. Border & Shape Language

### 5.1 Radius Scale
- `rounded-sm`: `4px` (`0.25rem`) — Micro badges, inline tags.
- `rounded-md` / `rounded-lg`: `8px` (`0.5rem`) — Action buttons, text inputs, navigation pills.
- `rounded-xl`: `12px` (`0.75rem`) — Standard glass cards and analytical bento panels.
- `rounded-full`: `9999px` — Status pills, avatar frames, rounded search bar, FAB button.

### 5.2 Border Rules & AI Highlights
- **Standard Border:** `1px solid #1E293B` or `border-outline-variant`.
- **Interactive Focus Border:** `focus:ring-1 focus:ring-primary focus:border-primary`.
- **AI Recommendation Border Accent:**
  - Left border line: `border-left: 2px solid #38BDF8;`
  - Tint fill: `background: linear-gradient(90deg, rgba(56, 189, 248, 0.05) 0%, transparent 100%);`
- **Severity Left Accent:** `border-l-4 border-l-primary`, `border-l-4 border-l-error`, `border-l-4 border-l-tertiary`.

---

## 6. Card Styles & Glassmorphism

### 6.1 Glass Card (`.glass-card` / `.glass-panel`)
```css
.glass-card {
  background: #111C2E;
  border: 1px solid #1E293B;
  border-radius: 0.75rem; /* 12px */
  transition: all 0.2s ease-in-out;
}

.glass-card:hover {
  border-color: rgba(56, 189, 248, 0.31); /* #38BDF850 */
  transform: translateY(-2px);
}
```

### 6.2 AI Recommendation Card
- Left border accent: `2px solid #38BDF8`.
- Subtly tinted background overlay with high contrast priority badge (`priority_high` icon with `bg-error-container/30`).

### 6.3 Header & Floating Glass Surfaces
- Glassmorphic top bar: `bg-surface/80 backdrop-blur-xl border-b border-outline-variant`.

---

## 7. Button System

### 7.1 Primary Cyan Button
- **Class:** `bg-primary text-on-primary font-bold rounded-lg px-md py-sm text-label-md`
- **Effects:** `hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-primary/20`
- **Usage:** Primary actions like "AI Report", "Apply Optimization", "Reorder Batch".

### 7.2 Secondary / Ghost Button
- **Class:** `bg-surface-container-high border border-outline-variant rounded-lg px-md py-sm font-label-md text-on-surface`
- **Effects:** `hover:bg-surface-container-highest transition-colors`
- **Usage:** Secondary actions like "Export Data", "Date Picker", "Filter Logs".

### 7.3 Risk / Urgent Action Button
- **Class:** `bg-error-container text-on-error-container rounded px-md py-xs font-label-md text-label-md`
- **Effects:** `hover:opacity-90 transition-opacity`
- **Usage:** Immediate stock reorder, emergency stop, route diversion.

### 7.4 Floating Action Button (FAB)
- **Class:** `fixed bottom-10 right-10 w-14 h-14 bg-primary text-on-primary rounded-full shadow-2xl flex items-center justify-center glow-cyan hover:scale-105 active:scale-95 transition-all z-40`
- **Shadow:** `.glow-cyan { box-shadow: 0 0 15px -3px rgba(56, 189, 248, 0.3); }`
- **Usage:** Trigger AI Copilot chat drawer or quick prompt modal.

---

## 8. Navigation Shell

### 8.1 Desktop Side Navigation Shell
- **Position & Dimensions:** Fixed left positioning, `width: 280px`, `height: 100vh`, `border-r border-outline-variant`.
- **Brand Header:** Icon container in `bg-primary-container` with `transit_enterexit` icon, title "AstraChain" in `text-primary`, subtitle "AI CONTROL TOWER" in uppercase `text-label-sm`.
- **Navigation Links:**
  - Active: `bg-secondary-container text-on-secondary-container rounded-lg border-l-2 border-primary scale-95`.
  - Inactive: `text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 transition-colors rounded-lg`.

### 8.2 Top Navigation Header
- **Position & Styling:** Sticky header (`h-16 px-lg bg-surface/80 backdrop-blur-xl border-b border-outline-variant`).
- **Global Search:** Pill search field (`w-96 bg-surface-container-low border border-outline-variant rounded-full pl-10 pr-4 py-2 text-body-md focus:ring-1 focus:ring-primary`).
- **User Identity:** Profile avatar with cyan border (`w-10 h-10 rounded-full border border-primary-container`), showing name ("Alex Rivera") and role badge ("Operations Lead").

### 8.3 Mobile Navigation Shell
- **Bottom Navigation Bar:** Fixed bottom bar (`fixed bottom-0 left-0 right-0 h-16 bg-surface/90 backdrop-blur-xl border-t border-outline-variant md:hidden z-50`).
- **5 Core Items:** Overview, Intel, AI, Reports, Settings.

---

## 9. Charts & Data Visualizations

### 9.1 Technical Chart Grid
- Background matrix: `.chart-grid` with 40px quadratic lines (`linear-gradient(to right, #1E293B 1px, transparent 1px), linear-gradient(to bottom, #1E293B 1px, transparent 1px)`).
- Axis lines: `border-l border-b border-outline-variant`.

### 9.2 Series & Predictive Curves
- **Historical Curve:** Solid Indigo (`#BDC2FF`), 3px stroke width.
- **Predictive Forecast Curve:** Dashed Cyan (`#38BDF8`), 3px stroke width (`stroke-dasharray="8,4"`).
- **Confidence Area:** Filled SVG region with low cyan opacity (`fill="rgba(56, 189, 248, 0.05)"`).
- **AI Confidence Pill:** Floating badge overlay (`bg-primary-container/20 border border-primary text-primary px-sm py-xs rounded text-[10px] font-bold`).

### 9.3 Timeframe Segmented Control
- Filter container: `bg-surface-container-low p-base rounded-lg border border-outline-variant`.
- Active segment: `bg-primary-container text-on-primary-container rounded-md px-sm py-xs text-label-sm`.

---

## 10. Data Tables

### 10.1 Table Architecture & Formatting
- **Table Container:** Glass panel with `overflow-x-auto border-collapse`.
- **Header Row (`<thead>`):**
  - Background: `bg-surface-container-high/30`
  - Text: `font-label-md text-label-sm text-on-surface-variant uppercase border-b border-outline-variant`
- **Body Rows (`<tbody>`):**
  - Border: `divide-y divide-outline-variant/30`
  - Hover transition: `hover:bg-surface-variant/20 transition-colors`

### 10.2 Special Cell Elements
- **SKU Tag:** `px-2 py-0.5 rounded bg-surface-variant text-[10px] uppercase font-bold tracking-wider`.
- **Days Remaining Progress Bar:**
  - Track: `w-16 h-1 bg-surface-container rounded-full overflow-hidden`
  - Fill: `bg-error` for low threshold, `bg-primary` for safe threshold.
- **Inline Action Button:** `text-primary hover:underline text-body-md font-medium flex items-center gap-xs`.

---

## 11. Status Indicators & Badges

### 11.1 Risk Severity Badges
- **High Risk:** `px-3 py-1 rounded-full bg-error/10 text-error text-label-sm font-bold border border-error/20`
- **Low Risk / Safe:** `px-3 py-1 rounded-full bg-primary/10 text-primary text-label-sm font-bold border border-primary/20`
- **Overstock / Warning:** `px-3 py-1 rounded-full bg-tertiary/10 text-tertiary text-label-sm font-bold border border-tertiary/20`

### 11.2 Metric Trend Indicators
- Positive Delta: `text-primary font-label-md flex items-center gap-xs` with `trending_up` icon.
- Risk Alert: `text-error font-label-md flex items-center gap-xs` with `notification_important` icon.

### 11.3 Health Progress Bars
- High-density telemetry bars: `h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden` with fill `bg-primary rounded-full`.

---

## 12. Responsive Behavior Matrix

| Viewport Breakpoint | Sidebar Behavior | Header / Nav Layout | Content Grid Layout |
| :--- | :--- | :--- | :--- |
| **Desktop (`>= 1024px`)** | Fixed left sidebar (`280px`) | Top bar with search input + profile | 4-col KPI grid, 3-col split analytics |
| **Tablet (`768px - 1023px`)** | Collapsed or icon rail (`72px`) | Top bar visible, search bar compact | 2-col KPI grid, stacked analytics |
| **Mobile (`< 768px`)** | Hidden sidebar (`hidden md:flex`) | Mobile top bar + bottom 5-tab bar | Single column vertical stack (`grid-cols-1`) |

---
