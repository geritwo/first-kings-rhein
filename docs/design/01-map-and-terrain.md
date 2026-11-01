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
- Implementation note (from the prototype): treat hex corners as graph nodes and hex edges as
  graph edges; weight edges (cheaper near hills/mountains sources, cheaper on province borders);
  run Dijkstra from a mountain corner to the map edge/coast or a confluence. Precompute, don't
  generate at render time.
- `PROPOSED` Rivers as natural province borders, trade/movement modifiers, watermill sites.

## Hidden content (see 06)
- `PROPOSED` Hidden, finite resource deposits revealed by exploration.
- `PROPOSED` Roman ruins as explorable sites (spolia, treasure, knowledge, road restoration).

## Per-hex state (summary — details in other files)
- terrain, river edges, owner (see 02), land use / development stage (see 02, 06),
  security value (see 07), visibility/explored flag.
