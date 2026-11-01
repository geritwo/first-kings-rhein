# F02 — Edge rivers

Status: **done** (2026-11-01) · Design: `01-map-and-terrain.md` § Rivers · Depends on: F01

## Goal
Rivers rise in the hills/mountains and run **along hex edges** downhill until they reach a lake or
join another river, and and are drawn as continuous lines between hexes.

## Scope (in)
- Replace the current through-hex-centre river walk (`World._generate_river`, `Tile.river_to`)
  with a **corner graph + Dijkstra**, precomputed once at map generation.
- 3–5 rivers per map (random count), starting at corners of hill/mountain hexes and ending at a
  corner that touches **water** (lake) or an **existing river** (confluence). The map edge is
  **not** a mouth.
- Rendering: each river is drawn as a polyline through hex corners (on the edges, not through centres).
- Keep the existing gameplay hook working: `Tile.river` = "this hex borders at least one river
  edge" → the existing +1 render on settled river hexes and the "folyó" hover label stay.
- Remove "rivers carve valleys" (mountain → hills on the course): edge rivers do not cross hexes.

## Out of scope
- Movement or territory cost for crossing a river edge (none now; currently rivers don't affect
  movement either). Hook left: `World.is_river_edge(a, b)` so `hexcore` cost callbacks can use it later.
- Rivers as province borders (`PROPOSED`); provinces are placed *after* rivers, so the
  "cheaper on province borders" weight from the design note is skipped.
- Trade/movement modifiers, watermills, fords/bridges, river width by flow, river names.

## Data model
- **Corner** key: `frozenset` of the 3 hexes meeting at it (off-map hexes allowed).
  Two corners are adjacent iff they share exactly 2 hexes; that pair is the edge between them.
- **Edge** key: `frozenset({a, b})` of the two hexes it separates.
- `World.rivers: list[list[corner]]` — ordered source → mouth, for drawing.
- `World.river_edges: set[edge]` — for lookups.
- `Tile`: `river_to` slot replaced by a `river` bool slot (set for hexes bordering a river edge).
- Pixel position of a corner = mean of the 3 hex centres (exact for a hex lattice), so no
  corner-index bookkeeping is needed in `main.py`.
- Helpers go in `hexcore.py`: `hex_corner_keys(h)`, `corner_neighbors(c)`, `corner_pixel(c, size)`.
- Tunables (module constants at the top of `world.py`, placeholder values) —
  `RIVER_COUNT = (3, 5)` (random, inclusive), `RIVER_MIN_LEN = 4` edges, `RIVER_MAX_LEN = 30` edges,
  `RIVER_SOURCE_SPACING = 6` hexes, `RIVER_UPHILL_PENALTY = 20`, `RIVER_NOISE = 0.15`.

## Rules (generation)
1. Corner elevation = mean `elev` of its on-map hexes.
2. **Sources:** corners of mountain hexes, then hill hexes, highest corner elevation first, skipping
   corners that touch water or are within `RIVER_SOURCE_SPACING` of an earlier source.
3. **Sinks:** any corner touching a water hex, or already on a river. Corners on the map border
   can be passed through but are not sinks.
4. **Dijkstra** from the source over the corner graph to the cheapest sink. Step cost
   `c1 → c2` = `1 + RIVER_UPHILL_PENALTY · max(0, elev(c2) − elev(c1)) + noise`, where noise is
   seeded (`self.rng`) and fixed per edge so results are deterministic. Steps cannot go along an
   edge between two off-map hexes. Effect: rivers flow downhill and meander a little.
5. Target count = `rng.randint(*RIVER_COUNT)`. Reject a river shorter than `RIVER_MIN_LEN`,
   longer than `RIVER_MAX_LEN` (no trekking across the map to a far lake), or with no reachable
   sink, and try the next source. If the sources run out first, the map has fewer rivers. This
   can happen on maps with few or no lakes.
6. Mark `river_edges` and set `Tile.river` on both sides of each edge.

## Opportunity / Constraint / Actor
No new buildings, techs or actions. Rivers keep their existing small render bonus (opportunity
for river-side settlements); constraints such as crossing costs come later (see Out of scope).

## Acceptance criteria (as tests in `tests/test_rivers.py`, stdlib `unittest`)
For seeds 0–49 at the default map size:
- At most 5 rivers. At least 1 on maps that have both lakes and hills/mountains. The share of
  seeds reaching 3+ rivers is reported and checked by hand, not asserted.
- Every pair of consecutive corners in a river shares exactly 2 hexes, at least one of them on the map.
- No river visits the same corner twice.
- The first corner touches a hill or mountain hex. The last corner touches water
  or a corner of an earlier river (never just the map edge). No earlier corner touches water.
- `Tile.river` is true exactly for on-map hexes that border a river edge.
- Same seed gives identical rivers.
- `python simulate.py 40 7` runs. A headless `main.Game(seed=7).draw()` runs under
  `SDL_VIDEODRIVER=dummy`.

## Design gaps
1. **Fertility bonus** stays at the prototype's +1 render for any settled hex that borders a river.
   Design hasn't decided this.
2. **Lake-less maps** can end up with fewer than 3 rivers (rule 5). Placeholder: accept that, and
   don't force lakes into terrain generation.

## Resolved (2026-11-01, chat)
- Tunables: module constants in `world.py`.
- Count: random 3–5.
- Mouth: a river must reach a lake or join a river. The map edge doesn't count.
