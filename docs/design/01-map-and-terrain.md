# 01 — Map & terrain

## Grid
- `DECIDED` Hex map, Civ-like look.
- `PROPOSED` Use **axial/cube coordinates** internally (clean neighbour/distance math); convert to
  offset rows only for rendering. (The early SVG prototype used odd-row offset coordinates.)

## Terrain
- `DECIDED` Civ-like terrain set, starting with **plains, hills, mountains**. Mountains appear in
  chains or standalone.
- `LEANING` Forest and marsh as additional types (relevant for clearing, hunting, wilderness).
- Terrain/biome drives: local building materials, resource deposits, ruler action costs,
  hunt prey, movement.

## Rivers
- `DECIDED` **Rivers run along hex edges, not through hexes.**
- `DECIDED` Hex corners are graph nodes and hex edges are graph edges. Rivers are precomputed at map
  generation with Dijkstra (downhill-weighted) from a mountain/hill corner.
- `DECIDED` A river must end at a **lake or a confluence** with another river. The map edge is
  **not** a mouth.
- `DECIDED` 3–5 rivers per map, random count. Tunables are constants in `world.py` for now.
- `LEANING` Settled hexes that border a river get +1 render (prototype value, not designed).
- `PROPOSED` River crossing cost for movement and territory. (The original note also proposed
  weighting river courses toward province borders. Not possible yet: provinces are placed after
  rivers.)
- `PROPOSED` Rivers as natural province borders, trade/movement modifiers, watermill sites.

## Hidden content (see 06)
- `PROPOSED` Hidden, finite resource deposits revealed by exploration.
- `PROPOSED` Roman ruins as explorable sites (spolia, treasure, knowledge, road restoration).

## Per-hex state (summary — details in other files)
- terrain, river edges, owner (see 02), land use / development stage (see 02, 06),
  security value (see 07), visibility/explored flag.
