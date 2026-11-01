# First Kings of the Rhine — Sandbox Empire prototype

Turn-based hex strategy prototype: the player is a Salian Frankish king from 481 AD,
growing a realm of provinces through clearing, building, royal visits and vassals.
Rules overview (Hungarian): see README.md.

<!-- Design notes from the browser chats go here once imported, e.g.: @DESIGN.md -->

## Running

- Python venv: `~/venv/first-kings-rhein` (Python 3.15). Use **pygame-ce**, not
  `pygame` — classic pygame has no wheel for 3.15 on this Mac and won't build.
- `python main.py [seed]` — the game (seed 7 is the usual test map)
- `python simulate.py [turns] [seed]` — headless run, for balancing
- UI can be smoke-tested headless with `SDL_VIDEODRIVER=dummy`, driving `Game`
  methods directly (`handle_key`, `handle_click`, `end_turn`, `draw`).

## Architecture

- `hexcore.py` — axial hex math (pointy-top), A*, Dijkstra flood-fill with a
  `cost(a, b)` callback; the same flood-fill does movement and territory claims.
- `world.py` — all game rules, **no pygame**. Must stay runnable headless.
  The UI only reads its state and calls its action methods.
- `main.py` — pygame UI: map, side panel, turn flow (auto-advance to the next
  item awaiting orders, blinking king focus, camera glide, end-of-turn prompt).

## Conventions

- In-game text, log messages and README: **Hungarian**. Code, identifiers,
  comments and docstrings: **English**.
- Tunable numbers are module-level constants at the top of `world.py` / `main.py`.
- Check balance changes with `simulate.py` before and after.
- No dependencies beyond pygame-ce.
- When adding a key binding, update the controls in the `main.py` docstring and
  the README table.

## Design state

Built: provinces with wild/field/village/town hexes, clearing, building lines,
seasons, local renders + silver/prestige/authority, loyalty, the king as a unit,
NPC lords acting on traits.

Not built yet:
- Province status never changes after map generation — no vassalizing,
  conquest or annexation of independent tribes.
- Knights (`World.knights`) are counted and shown, but used for nothing.
