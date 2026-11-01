# F02 — Edge rivers

Status: **done** (2026-11-01; revised same day: more, longer, curvier rivers + islands; then
coast, sea and major rivers) · Design: `01-map-and-terrain.md` § Rivers · Depends on: F01

## Goal
Rivers rise in the hills/mountains and run **along hex edges** downhill until they reach the sea, a
lake or another river, and are drawn as continuous lines between hexes. Every map has a coast and
at least two major rivers (Rhine/Loire-like) crossing its central plains to the sea.

## Scope (in)
- Replace the current through-hex-centre river walk (`World._generate_river`, `Tile.river_to`)
  with a **corner graph + Dijkstra**, precomputed once at map generation.
- **Coast:** one side per map, chosen at random from west, north-west and north, has **sea** on
  at least 30% of its map border. Sea is a new terrain, `sea` ("Tenger"), with the same rules as
  lakes. The coast is shaped by lowering elevation towards that side, so bays come from noise.
  The land also tilts gently upwards away from the coast, so rivers drain towards it.
- 5–9 rivers per map (random count), ending at a corner that touches **water** (lake or sea) or an
  **existing river** (confluence). The map edge is **not** a mouth, and rivers never run along the
  map border.
- **Major rivers (2):** rise on the far side from the coast, pass a flat corner in the central
  plains and end at the **sea**. They are drawn thicker. The other rivers rise in hills or
  mountains and mostly end up as tributaries.
- Rivers **meander**, more strongly on flat land (plains, forest, marsh) than in hills.
- **Islands:** a river may split round one flat hex and rejoin downstream. That hex gets river
  edges on all 6 sides.
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
- `World.coast_side: str` — `west` | `northwest` | `north`.
- Terrain `sea` in `TERRAIN`; `WATER = ("water", "sea")`.
- `World.rivers: list[list[corner]]` — main courses, ordered source → mouth, for drawing.
- `World.n_major_rivers: int` — `rivers[:n]` are the major rivers.
- `World.river_branches: list[list[corner]]` — island side channels, ordered downstream; both
  ends lie on their parent river.
- `World.river_edges: set[edge]` — for lookups.
- `Tile`: `river_to` slot replaced by a `river` bool slot (set for hexes bordering a river edge).
- Pixel position of a corner = mean of the 3 hex centres (exact for a hex lattice), so no
  corner-index bookkeeping is needed in `main.py`.
- Helpers go in `hexcore.py`: `hex_corner_keys(h)`, `corner_neighbors(c)`, `corner_pixel(c, size)`.
- Tunables (module constants at the top of `world.py`, placeholder values) —
  coast: `COAST_SIDES`, `COAST_MIN_SHARE = 0.30`, `COAST_DROP = 0.45`, `COAST_WIDTH = 3` hexes
  (grown by 0.5 until the share is met), `COAST_BAY_AMP = 3` hexes, `REGION_TILT = 0.14`,
  `SEA_LEVEL = 0.26`;
  majors: `RIVER_MAJOR_COUNT = 2`, `RIVER_MAJOR_FAR = 0.55`, `RIVER_MAJOR_SPACING = 8` hexes,
  `RIVER_MAJOR_MAX_LEN = 160`, `RIVER_CENTRE = (0.3, 0.7)`, `RIVER_REPEL = 3`;
  `RIVER_COUNT = (5, 9)` (random, inclusive, majors included), `RIVER_MIN_LEN = 8`,
  `RIVER_MAX_LEN = 70` edges,
  `RIVER_SOURCE_SPACING = 4` hexes, `RIVER_UPHILL_PENALTY = 20`, `RIVER_STEP_COST = 0.3`,
  `RIVER_FLAT = (plains, forest, marsh)`, `RIVER_MEANDER_FLAT = 12`, `RIVER_MEANDER_HILL = 1.5`,
  `RIVER_MEANDER_FLOOR = 0.4`, `RIVER_MEANDER_FREQ = 0.35` per hex, `RIVER_ISLAND_CHANCE = 0.5`.
- Rivers use their own RNG (`Random(seed·7919 + 2)`), so retuning rivers doesn't reshuffle
  provinces and the rest of a seed's map.

## Rules (generation)
0. **Terrain:** `elev = fbm + REGION_TILT·(d/dmax − ½) − COAST_DROP·max(0, 1 − (d + bay)/width)`,
   where `d` is the distance in hexes from the coast side. Sea = hexes below `SEA_LEVEL` that are
   connected to that side's border. Other hexes below `SEA_LEVEL` are lakes. The width grows until
   at least 30% of the border is sea. The coast side has its own RNG (`Random(seed·7919 + 1)`).
1. Corner elevation = mean `elev` of its on-map hexes.
2. **Sources:** corners of mountain hexes, then hill hexes, highest corner elevation first, skipping
   corners that touch water or are within `RIVER_SOURCE_SPACING` of an earlier source.
3. **Sinks:** any corner touching a water hex, or already on a river (incl. island channels).
4. **Dijkstra** from the source over the corner graph to the cheapest sink. Step cost
   `c1 → c2` = `RIVER_STEP_COST + RIVER_UPHILL_PENALTY · max(0, elev(c2) − elev(c1))
   + amp · max(0, n(c2) − RIVER_MEANDER_FLOOR)`. Here `n` is a smooth 2-octave fBm field with its
   own seed per river, and `amp` is `RIVER_MEANDER_FLAT` when both hexes of the edge are flat,
   `RIVER_MEANDER_HILL` otherwise. The base step is cheap, so rivers take detours to follow the
   field's low "valleys" and bend at a scale of about 1/`RIVER_MEANDER_FREQ` hexes. Edges with an
   off-map hex are not allowed. Effect: rivers flow downhill, run fairly straight in hills and
   wind on flat land.
5. Target count = `rng.randint(*RIVER_COUNT)`. Reject a river shorter than `RIVER_MIN_LEN`,
   longer than `RIVER_MAX_LEN` (no trekking across the map to a far lake), or with no reachable
   sink, and try the next source. If the sources run out first, the map has fewer rivers. This
   can happen on maps with few or no lakes.
6. Mark `river_edges` and set `Tile.river` on both sides of each edge.
7. **Major rivers first.** Sources are corners beyond `RIVER_MAJOR_FAR` of the max coast distance,
   at least `RIVER_MAJOR_SPACING` apart (hills and mountains first, then the highest lowland as a
   fallback). Leg 1 runs Dijkstra to the **nearest** free flat corner in the central box
   (`RIVER_CENTRE` of width and height), at least `RIVER_MAJOR_SPACING` from the other waypoints.
   Leg 2 goes from there to the first corner touching the sea. Both legs avoid lakes, existing
   rivers and their own course. Routing to the nearest waypoint, rather than a random one, keeps
   majors from detouring round each other.
8. **No parallel runs:** stepping onto a corner within one hex of an existing river costs
   `RIVER_REPEL` extra (all rivers). Rivers then join or keep apart instead of running side by side.
9. **Island:** with chance `RIVER_ISLAND_CHANCE`, look for a flat hex (with all neighbours on the map)
   that the new river runs along for 2–3 consecutive edges. Add the other side of that hex as a
   branch, provided its inner corners are not on a river and don't touch water. One island per
   river at most; pick at random among the candidates.

## Opportunity / Constraint / Actor
No new buildings, techs or actions. Rivers keep their existing small render bonus (opportunity
for river-side settlements); constraints such as crossing costs come later (see Out of scope).

## Acceptance criteria (as tests in `tests/test_rivers.py`, stdlib `unittest`)
For seeds 0–49 at the default map size:
- At most 9 rivers. At least 1 on maps that have both water and hills/mountains. The share of
  seeds reaching 5+ rivers is reported and checked by hand, not asserted.
- The coast side is one of W/NW/N, and at least 30% of its border hexes are sea.
- At least 2 major rivers, each ending at a sea corner and passing a flat corner in the central box.
- Every pair of consecutive corners in a river shares exactly 2 hexes, both of them on the map.
- Every island branch starts and ends on its parent river (in downstream order) and goes round
  exactly one hex, which has river edges on all 6 sides. At least one island occurs across the seeds.
- No river visits the same corner twice.
- The first corner of a minor river touches a hill or mountain hex. The last corner touches water
  or a corner of an earlier river or its island channel (never just the map edge). No earlier corner touches water.
- `Tile.river` is true exactly for on-map hexes that border a river edge.
- Same seed gives identical rivers.
- `python simulate.py 40 7` runs. A headless `main.Game(seed=7).draw()` runs under
  `SDL_VIDEODRIVER=dummy`.

## Design gaps
1. **Fertility bonus** stays at the prototype's +1 render for any settled hex that borders a river.
   Design hasn't decided this.
2. **Lake-less maps** can end up with fewer than 5 rivers (rule 5). Placeholder: accept that, and
   don't force lakes into terrain generation. Seeds 0–49 all reach 5–9.
3. **Fewer provinces fit** because the sea takes land. Over seeds 0–49 the average is 21.3, against
   21.6 before; the lowest is 16, against 19. Province placement isn't changed here.
4. **Sea is just impassable water** for now. Coastal trade, ports and raids from the sea are
   not designed yet.
5. **Islands are only visual so far.** No rules for island hexes (defence, mills, crossings).

## Resolved (2026-11-01, chat)
- Tunables: module constants in `world.py`.
- Count: random 3–5. **Superseded** (same day): random 5–9, longer, curvier on flat land, islands.
- Mouth: a river must reach a lake or join a river. The map edge doesn't count.
- Coast: one random side from W / NW / N, with at least 30% of that border as sea.
- Sea is its own terrain ("Tenger").
- At least 2 major rivers cross the central plains and flow to the sea.
