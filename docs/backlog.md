# Backlog

Vertical slices, each playable/testable on its own. Status: `todo` / `spec` / `doing` / `done`,
plus `proto` = something exists in the prototype code but doesn't match the design yet.
Statuses audited against the code on 2026-11-01 — see *Audit notes* below.
Pick one item at a time; write its spec in `docs/specs/<ID>-<slug>.md`.

| ID | Feature | Depends on | Design | Status |
|---|---|---|---|---|
| F01 | Hex map core: coordinates, terrain gen, rendering, camera | — | 01 | done |
| F02 | Edge rivers (corner graph + Dijkstra, precomputed) | F01 | 01 | done |
| F03 | Turn loop + point accumulation + simple HUD | F01 | 06 | proto |
| F04 | Provinces with fixed borders, seat hex, per-hex ownership | F01 | 02 | proto |
| F05 | Ruler unit: movement, travel income, province depletion | F03, F04 | 03 | proto |
| F06 | Local buildings as province modifiers (local materials) | F03, F04 | 06 | proto |
| F07 | Nobles: feudal graph + loyalty 1–5 + production modifier | F04 | 04 | proto |
| F08 | Knights: create estates from common land (tax-free, +army) | F04, F07 | 02 | todo |
| F09 | Conversion + bishopric/palace per province, clergy pool | F06 | 05 | proto |
| F10 | Church tech tree (know + build) | F09 | 05 | todo |
| F11 | Church as autonomous actor (stats, demands) | F10, F16 | 05 | todo |
| F12 | Resources MVP-8 + hidden deposits + exploration | F01, F03 | 06 | todo |
| F13 | Clearing chain + frontier expansion | F04, F12 | 02 | proto |
| F14 | Barbarians + per-hex security value | F01, F03 | 07 | todo |
| F15 | Trade routes (distance tiers, capacity; requires security) | F12, F14 | 06 | todo |
| F16 | Event engine (data-driven incidents) | F03 | 08 | todo |
| F17 | Ruler actions: court, feast, hunt | F05, F07, F16 | 03 | proto |
| F18 | Relationship ladder for all actors | F07 | 04 | todo |
| F19 | Scripted rivals (2–3, archetypes) | F18 | 07 | proto |
| F20 | Towns chain (market → rights → guilds → bishopric / free town) | F06, F15 | 06 | proto |
| F21 | Entrenchment meter (appointed → hereditary) | F07 | 02 | todo |
| F22 | Coronation, legitimacy pillars, stealable crown, victory | F09, F18 | 00 | todo |

## Suggested first loop
F01 → F03 → F04 → F05 gives a playable "king rides around and collects" core; everything else
plugs into that.

## Audit notes (2026-11-01)
What the prototype (`hexcore.py`, `world.py`, `main.py`) already has, and where it differs from the design.

- **F01 done** — axial pointy-top coordinates, terrain gen (plains, forest, hills, marsh, mountain,
  lake), cached map rendering, camera pan/drag/glide.
- **F02 done** (2026-11-01) — 3–5 rivers along hex edges (corner graph + Dijkstra) from
  hills/mountains to a lake or a confluence; see `docs/specs/F02-edge-rivers.md`. No movement or
  border effects yet (`World.is_river_edge` is the hook).
- **F03 proto** — seasonal turn loop (481 spring, autumn harvest), top-bar HUD. Point types are the
  prototype's own: local renders (spoil 15%/season), silver, prestige (decays), authority (cap 20).
- **F04 proto** — provinces with a seat hex and per-hex `owner`, but borders are **not fixed**: claims
  are a flood-fill from settled hexes and grow with clearing. No owner types (crown/count/knight/…).
- **F05 proto** — ruler unit with movement points, A* paths, roads. No travel income or depletion;
  his presence only gives free vassal orders, feasts and loyalty gain.
- **F06 proto** — building lines with tiers (fort, church, monastery, market, royal palace) acting as
  province modifiers. No local materials.
- **F07 proto** — every province has a lord with a trait; loyalty has **4 levels** (design: 1–5) and
  multiplies production; decays after 8 seasons without a royal visit. No feudal graph.
- **F08 todo** — knights are only a count of fort tiers (`World.knights`), unused. No estates.
- **F09 proto** — church line converts the province (pagan → mixed → Christian) and gives authority.
  No bishopric/palace per province, no clergy pool.
- **F13 proto** — clearing chain wild → field → village (autumn growth) → town quarter, frontier
  expansion via territory claims. Conflicts with fixed borders (F04) — needs a design decision.
- **F17 proto** — feast only (store cost → prestige + loyalty), no incident table. No court or hunt.
- **F19 proto** — independent tribes are AI lords choosing build/clear by trait; no scripted rivals,
  archetypes or diplomacy. Province status never changes after map generation.
- **F20 proto** — town-quarter hexes and a market line (depot → market → fair; bonus on Roman roads).
  No rights, guilds or free towns.
- **todo, nothing in code:** F10, F11, F12, F14, F15, F16, F18, F21, F22.
