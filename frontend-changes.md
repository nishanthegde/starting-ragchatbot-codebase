# Frontend Changes

## What was added/changed
- Added an icon-based theme toggle button (`sun`/`moon`) fixed to the top-right corner.
- Implemented smooth icon crossfade/rotation and color transitions when toggling themes.
- Added keyboard and accessibility support for the toggle (`button` semantics, `aria-pressed`, dynamic `aria-label`, focus-visible states).
- Added a light theme variant by overriding existing CSS variables while preserving the existing dark aesthetic as default.
- Persisted theme preference in `localStorage` when available.

## Files touched
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

## New dependencies
- None

## Assumptions
- The existing dark theme remains the default experience.
- If `localStorage` is unavailable, the app still works and falls back to the default theme.
