# First Kings — early-medieval hex 4X

Turn-based 4X on a hex map. The player is an early-medieval ruler after the fall of Rome who
unifies a kingdom by founding and organizing **provinces** (not cities). Base cultural model:
Rhineland / Lotharingian (Ottonian–Salian, ~950–1075); other cultures may come later as variants.

## Tech
- Python 3.15, **pygame-ce** (not `pygame` — no 3.15 wheels), venv at `~/venv/first-kings-rhein`.
  No other dependencies.
- Run: `python main.py [seed]` — random map without a seed; seed 7 is the usual test map.
- Headless rules run: `python simulate.py [turns] [seed]` (defaults 40, 7) — prints a per-province
  summary before/after. Player provinces stay idle; only NPC lords act. Use it to check balance.
- Test: `python -m unittest discover tests` (stdlib unittest: `tests/test_rivers.py`, `tests/test_meters.py`). UI can be smoke-tested headless with `SDL_VIDEODRIVER=dummy`,
  constructing `main.Game(seed=7)` and driving `handle_key` / `handle_click` / `end_turn` / `draw`.

## Code (current prototype)
- `hexcore.py` — axial pointy-top hex math, A*, and a multi-source Dijkstra `flood_fill` taking a
  `cost(a, b)` callback. The same flood-fill drives ruler movement range *and* territory claims
  (each province claims hexes within `TERRITORY_BUDGET` of its settled hexes; nearest source wins).
- `world.py` — all rules, **no pygame**; must stay runnable headless. `World.end_turn()` is the
  season pipeline: NPC/unordered-vassal actions → projects advance → yields & spoilage → autumn
  village growth → loyalty → time advance → `recompute_territory()`. Player orders go through
  `can_order` / `_pay_order` (one order per province per turn; vassals cost AU unless the king is present).
- `main.py` — pygame UI only reads `World` state and calls its action methods. Owns turn flow:
  `refresh_pending` / `advance` focus the next item awaiting orders (king blinks, provinces get
  selected), camera glides via `cam_target`, end-of-turn banner when nothing is pending.
- In-game text, log messages and README are Hungarian; code and comments are English. New key
  bindings go in the `main.py` docstring and the README controls table.
- Tunables are mostly module-level constants at the top of `world.py` / `main.py`. The exception is
  the province meters (F07b, Integration / Settlement): their thresholds and values are in
  `data/province_meters.json` (stdlib `json`), the repo's first data file; new data-driven
  tunables should follow that pattern.

**The prototype predates the design docs and diverges from them** — e.g. it starts in 481 with
Salian Franks (not ~950–1075 Rhineland), provinces grow by clearing (not fixed borders), loyalty
has 4 states (design: 1–5), and province status never changes after map generation. Treat the
code as a starting point, not as decided design.

## How we work (read this first)
- **Iterative, one feature at a time.** Pick an item from `docs/backlog.md`. Implement only that
  item's agreed scope. Don't build neighbouring systems "while you're there" — stub them behind a
  small interface and note the stub in the spec.
- **Design questions → ideas + a plan, not code.** When I ask a design question, answer with
  options, trade-offs and a proposed plan. Implement only when I explicitly say so
  ("implement", "go", "build it").
- **Spec before code.** Every feature gets a short spec in `docs/specs/` (scope, data model, rules,
  acceptance criteria, out of scope). Wait for my approval before coding. Use the `feature` skill.
- **Design docs are the source of truth.** Before working on a system, read its file in
  `docs/design/` and `docs/decisions.md`. Don't load all design files up front — read the ones the
  task needs.
- **Keep docs in sync.** When a decision is made or changed (in chat or during implementation),
  update the design file and append a line to `docs/decisions.md`. New unknowns go to
  `docs/open-questions.md`. Design changes coming from claude.ai arrive as a "design delta" —
  apply them with the `design-sync` skill.
- **Status tags in design docs** — respect them:
  - `DECIDED` — agreed, build to it
  - `LEANING` — current direction, may change; ask if it matters
  - `PROPOSED` — Claude's earlier suggestion, *not* accepted; never treat as a requirement
  - `OPEN` — undecided; ask, or pick the simplest placeholder and flag it
  - `DEFERRED` — explicitly out of scope for now
- **Data-driven tuning.** Costs, yields, thresholds and probabilities live in data files, not in code.

## Core design principles
1. **Every development opens a possibility AND creates a constraint.** Describe each building /
   tech / action with the template: *Opportunity / Constraint / Actor affected*.
2. **Hex-level granularity** over province-level abstraction (land ownership is tracked per hex).
3. **Historically grounded, then simplified.** Mechanics derive from real medieval institutions.
4. **Core engine loop:** accumulate point types → spend them on local buildings/actions that act as
   province modifiers.
5. **One unified relationship ladder** for every political actor (own nobles and foreign powers).

## Design map
| File | Covers |
|---|---|
| `docs/design/00-vision.md` | Pitch, setting, victory (coronation + crown), scope |
| `docs/design/01-map-and-terrain.md` | Hex grid, terrain, edge rivers, hidden content |
| `docs/design/02-provinces-and-land.md` | Province structure, per-hex ownership, knights, clearing, entrenchment |
| `docs/design/03-ruler-and-court.md` | Ruler unit, travel economy, royal actions |
| `docs/design/04-nobility-and-diplomacy.md` | Feudal graph, loyalty, relationship ladder, vassals |
| `docs/design/05-church.md` | Conversion, clergy, church tech tree, Church as actor |
| `docs/design/06-economy-and-towns.md` | Points, resources, chains, trade, towns, taxation |
| `docs/design/07-world-and-opponents.md` | Start scenario, rivals, barbarians, security |
| `docs/design/08-events.md` | Unified incident/event engine |
| `docs/decisions.md` | Dated decision log |
| `docs/open-questions.md` | Unresolved design questions |
| `docs/backlog.md` | Feature slices, dependencies, status |
