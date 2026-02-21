# Frontend Changes

## What was added/changed
- Added an accessible icon-based theme toggle button (`sun`/`moon`) in the top-right corner of the UI.
- Implemented light/dark theme switching with smooth icon transitions and subtle theme color transitions.
- Added keyboard-accessible focus-visible styling for the toggle button and updated ARIA state (`aria-pressed`, `aria-label`) dynamically.
- Persisted the selected theme in `localStorage` and initialized theme on page load using stored preference, with system preference fallback.
- Added a stronger light theme palette with:
  - lighter backgrounds and surfaces
  - darker body/secondary text for improved contrast
  - updated primary/hover colors for interactive controls
  - accessible border and status colors
- Replaced hardcoded component colors (sources chips, source summary controls, code blocks, status messages, button hover shadow) with semantic CSS variables so light and dark themes stay consistent and readable.
- Enhanced theme toggle behavior in JavaScript to switch themes on button click with `startViewTransition` when supported, and graceful fallback when unavailable or reduced-motion is enabled.
- Added view-transition timing styles for smoother theme changes and reduced-motion handling for transition animations.
- Finalized variable-driven theming details:
  - explicitly using `body[data-theme="light"]` + CSS custom properties as the source of truth for theme values
  - mapped remaining hardcoded primary-on-color usage to CSS variables (`--on-primary`) for button and user-message text
  - switched assistant message bubble background to theme token (`--assistant-message`) to preserve hierarchy in both themes
- Bumped static asset cache-busting query strings in `index.html` (`style.css` to `v=14`, `script.js` to `v=12`).

## Files touched
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`
- `frontend-changes.md`

## New dependencies
- None.

## Assumptions
- The toggle is intended to switch between dark and light UI themes.
- No frontend build pipeline is configured for this static frontend; validation was performed with `node --check frontend/script.js`.
- Accessibility target is practical high-contrast defaults for normal text and interactive states across the existing UI components.
