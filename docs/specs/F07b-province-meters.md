# F07b — Province meters: Integration & Settlement

Status: **spec, awaiting approval** (2026-11-11) · Design: `02-provinces-and-land.md` § Integration &
Settlement, `04-nobility-and-diplomacy.md`, `08-events.md` · Depends on: F04, F07

## Goal
Every province shows two meters — **Integration** (0–5) and **Settlement** (0–4) — that only rise
as the king's provinces develop, plus a derived **tension** value. The player can read them in the
province panel, and the numbers are ready for knights (F08) and events (F16) to use later.

## Scope (in)
- Two stored levels per province, each with a hidden progress counter that fills every season and
  raises the level when it passes a threshold (ratchet: never decreases).
- Start values by province type (see Rules), loaded from a data file.
- Progress only for **player provinces** (royal and vassal). Independent provinces keep their
  start values.
- `World.tension(p)`: derived from the two levels, not stored.
- `World.tension_weight(p)`: the weight a future tension event would get. **Stub**: nothing fires.
- Province panel and `simulate.py` summary show the meters (numbers, no level names).
- Tests for the acceptance criteria below.

## Out of scope (and what stands in)
- **Bringing an independent province under the crown** (submission, annexation, status change):
  F18. Until then every independent province keeps 0/0, and the meters have nothing to do for
  Roman-Gallic or tribal provinces in normal play. Tests change `p.status` directly.
- **Firing tension events:** F16 (event engine). `tension_weight` is the only hook.
- **Knight estates unlocked by Settlement 3–4:** F08. The level is just a readable field.
- **Hereditary status needing a high Integration level:** F21.
- **Real levers** — royal grants, organised clearing, native vs. Frankish count, keeping Roman law,
  placitum, hostages, godparenthood, bishop's palace. The placeholder levers below use only what
  the prototype already has.
- **Level names.** The UI shows `n/5` and `n/4`.

## Data model
- `Province.integration`, `Province.settlement`: ints (levels).
- `Province.integration_progress`, `Province.settlement_progress`: floats. Progress is cumulative
  and never reset, and the thresholds are cumulative too (e.g. level 2 needs a total of 8).
- New data file `data/province_meters.json`, loaded once by `world.py` with stdlib `json`
  (no new dependency). Contents:
  ```json
  {
    "integration_thresholds": [3, 8, 15, 25, 40],
    "settlement_thresholds": [3, 8, 15, 25],
    "integration_levers": { "church_per_tier": 1, "ruler_present": 2 },
    "settlement_levers": { "per_knight": 0.5 },
    "start": {
      "player_provinces": { "integration": 5, "settlement": 4 },
      "others": { "integration": 0, "settlement": 0 }
    },
    "tension_base_weight": 10
  }
  ```
  All numbers are placeholders. The `World` takes the loaded dict (injectable in tests).
- This is the first data file in the repo. The prototype keeps tunables as constants in
  `world.py`; see Design gaps 1.

## Rules
Start (at map generation, after `_place_provinces`): provinces whose status is `royal` or `vassal`
get the `player_provinces` values (nothing to integrate or settle: own culture, the king's own
average province). All others get `others`.

Each season, in `World.end_turn()` as a new step **5b**, after loyalty and before time advances,
for every player province `p`:
- Integration progress `+= church_per_tier · (best church tier + 1)` if the province has a church
  line (the prototype's conversion line, tiers 0–3), `+= ruler_present` if the king is in `p`.
- Settlement progress `+= per_knight · knights(p)`.
- While progress `≥ thresholds[level]` and the level is below its maximum, the level rises by 1.
  A level-up writes one Hungarian log line for player provinces.

Tension: with `i = integration / 5` and `s = settlement / 4`, `tension(p) = |i − s|` (0..1).
`tension_weight(p) = tension_base_weight · tension(p)`. Both are pure functions, no state.

Meters never decrease. There is no decay, and nothing in this slice lowers a level.

## Opportunity / Constraint / Actor
No new buildings or actions. The existing ones gain a second role:
- **Church line.** Opportunity: raises Integration, so a province can be bound to the crown.
  Constraint: it only counts in player provinces, and it costs its normal build time and price.
  Actor: the native population.
- **Royal presence.** Opportunity: speeds Integration. Constraint: the king can be in one province
  per season, so the others do not gain from this lever.
  Actor: the native population.
- **Forts / knights.** Opportunity: raise Settlement, binding the warrior class to the land.
  Constraint: Settlement racing ahead of Integration raises tension (which will mean incidents
  once F16 exists). Actor: the incoming warrior class.

## Acceptance criteria (as tests in `tests/test_meters.py`, stdlib `unittest`)
For seeds 0–9:
- Every province has `0 ≤ integration ≤ 5` and `0 ≤ settlement ≤ 4`.
- At the start, royal and vassal provinces are at 5/4 and every other province at 0/0.
- Over 40 seasons of `simulate`-style play, no level ever decreases.
- Independent provinces keep their levels and progress at 0 for all 40 seasons.
- On a test world where a Roman-Gallic province is set to `vassal` with start 0/0: with a church of
  tier ≥ 0 its Integration level rises within 40 seasons, never exceeds 5, and rises exactly when
  its progress passes the threshold.
- Same with a fort and Settlement, never exceeding 4.
- With the king staying in that province, its Integration progress per season is higher by exactly
  `ruler_present` than without.
- `tension` is 0 when both meters are at their maximum or both at 0, and always in `[0, 1]`.
  `tension_weight` is `tension_base_weight · tension`.
- Changing a value in an injected data dict changes the behaviour (thresholds and lever sizes
  are not in code).
- Same seed gives identical meters (no randomness is used).
- `python simulate.py 40 7` runs and prints the meters. A headless `main.Game(seed=7).draw()` runs
  under `SDL_VIDEODRIVER=dummy` with the new panel lines.

## Design gaps
1. **Data file format.** CLAUDE.md wants tunables in data files, but the repo has none, and the
   `08-events.md` sketch uses YAML while the project has no dependencies beyond pygame-ce.
   Placeholder: JSON in `data/`, loaded with the stdlib. The river constants stay as they are.
2. **Normal play shows almost nothing yet.** Without F18 no independent province can be brought
   under the crown, so the player's own provinces sit at the maximum and the meters only move in
   tests. Placeholder: accept that, and keep the slice to the foundation.
3. **Start values.** The design says own culture starts higher (`PROPOSED`). Placeholder: the
   king's provinces start at the maximum (Settlement at maximum is `DECIDED`), everything else at 0.
4. **Levers and numbers** (thresholds, lever sizes) are placeholders; the real levers
   are `PROPOSED` in 02.
5. **Tension formula** is a symmetric gap of the two fractions. The design only says "derived from
   the gap", so which direction hurts more is open.
6. **Conversion vs. Integration.** The prototype's `religion` stays untouched and separate, and the
   church line feeds Integration as a lever. Whether conversion belongs to Integration is `OPEN`.
