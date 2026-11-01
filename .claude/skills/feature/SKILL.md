---
name: feature
description: Start or continue one backlog feature of First Kings (e.g. "/feature F05") — spec, plan, implement only after approval, then update docs and backlog.
---

# Feature workflow

Argument: a backlog ID (e.g. `F05`) or a short feature description.

## 1. Orient
- Find the item in `docs/backlog.md`. If it isn't there, propose an ID and a row and stop for approval.
- Read only the design files listed for it in `docs/design/`, plus `docs/decisions.md`.
- Check what already exists in the code for this feature and its dependencies.

## 2. Spec (no code yet)
Write `docs/specs/<ID>-<slug>.md` with:
- **Goal** — one sentence, player-visible
- **Scope (in)** — the smallest version that is playable/testable
- **Out of scope** — and which stubs/interfaces stand in for missing systems
- **Data model** — classes/fields, data files for tunables
- **Rules** — turn-by-turn behaviour, formulas with placeholder numbers
- **Opportunity / Constraint / Actor** — for each new building, tech or action
- **Acceptance criteria** — checkable statements, ideally as tests
- **Design gaps** — anything `OPEN` or `PROPOSED` the spec depends on, with the placeholder chosen

Then stop and ask me to approve or change the spec. Ask about `OPEN` items that matter; never treat
`PROPOSED` as decided.

## 3. Implement (only after explicit approval)
- Keep to the approved scope. Tunables go in data files.
- Add tests for the acceptance criteria.
- Run the game/tests before reporting done.

## 4. Close
- Set the backlog status.
- Append any decision made along the way to `docs/decisions.md` (source: `impl`) and update the
  design file's status tags.
- Add new unknowns to `docs/open-questions.md`.
- Summarise: what's playable now, what's stubbed, suggested next item.
