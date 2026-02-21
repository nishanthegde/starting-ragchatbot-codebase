---
name: implement-frontend-feature
description: >
  Use this when the user asks to implement a NEW FEATURE in the frontend UI.
  Do NOT use for backend changes, infra changes, or refactors unrelated to a feature.
---

# Implement Frontend Feature

You are implementing a new feature in this codebase.

## Scope and constraints
- Only modify files under `frontend/`.
- Do not modify backend code.
- Do not modify infra/config outside `frontend/`.

## Deliverables
- Implement the requested feature.
- Write or update `frontend-changes.md` at the repository root describing:
  - What was added/changed
  - Files touched
  - Any new dependencies
  - Any assumptions

You may write to `frontend-changes.md` without asking for additional permission.

## Workflow
1. Restate the feature request in your own words.
2. Identify the relevant frontend entry points and files.
3. Implement the change.
4. Run the frontend checks/build if available.
5. Update `frontend-changes.md` with a concise change log.
6. Follow any testing protocols in AGENTS.md