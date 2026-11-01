# Decision log

Append-only. Format: `date | area | decision | source`. Source = `chat` (claude.ai design chats)
or `impl` (made during implementation). When a decision is superseded, add a new line and mark the
old one `(superseded)`.

| Date | Area | Decision | Source |
|---|---|---|---|
| 2026-10-18 | vision | Provinces, not cities, are the core unit; early medieval, post-Rome | chat |
| 2026-10-18 | vision | Victory: coronation as milestone, holding unity afterwards wins | chat |
| 2026-10-18 | vision | Crown is a movable, stealable artifact | chat |
| 2026-10-18 | principle | Every development = opportunity + constraint (Opportunity/Constraint/Actor template) | chat |
| 2026-10-18 | economy | Core loop: accumulate point types, spend on local facilities as province modifiers | chat |
| 2026-10-18 | economy | Buildings use local materials (biome/culture dependent) | chat |
| 2026-10-18 | church | Bishopric + bishop's palace in every province; clergy is a headcount pool | chat |
| 2026-10-18 | church | Civ-like church tech tree: know (research) + build locally | chat |
| 2026-10-18 | church | Church is an autonomous actor | chat |
| 2026-10-18 | ruler | Ruler is a mobile unit with per-province actions; tournaments dropped | chat |
| 2026-10-18 | ruler | Succession deferred (maybe random event) | chat |
| 2026-10-18 | ruler | No income at start beyond own province; travel to collect; staying depletes | chat |
| 2026-10-18 | nobility | Nobility starts as local loyalty modifier on production | chat |
| 2026-10-18 | nobility | Per-noble loyalty 1–5; low loyalty → no war help, rebellion, punishment | chat |
| 2026-10-18 | provinces | Province = 1-hex seat + 1-hex knight estates + common land | chat |
| 2026-10-18 | provinces | Knight estates pay no tax, only add army; consume common land | chat |
| 2026-10-18 | provinces | Starting province 7 hexes (superseded) | chat |
| 2026-10-18 | provinces | Provinces have more than 7 hexes (supersedes 7) | chat |
| 2026-10-18 | provinces | King's province is average; advantage only via royal actions | chat |
| 2026-10-18 | map | Rivers along hex edges; Civ-like terrain (plains, hills, mountains in chains/standalone) | chat |
| 2026-10-18 | provinces | Land ownership tracked per hex | chat |
| 2026-10-18 | setting | Base model Rhineland/Lotharingian; culture variants later | chat |
| 2026-10-18 | provinces | Count rootedness meter; hereditary status built via the meter | chat |
| 2026-10-18 | provinces | Fixed province borders with internal wilderness ring; frontier only at realm edge | chat |
| 2026-10-18 | world | Start: tribes, surviving bishoprics, southern kingdoms/city-states | chat |
| 2026-10-18 | world | 2–3 random scripted rivals; frontier barbarians must be suppressed for trade/new land | chat |
| 2026-10-24 | diplomacy | One unified relationship ladder for all political actors | chat |
| 2026-10-24 | diplomacy | Marriage abstract for now | chat |
| 2026-10-24 | diplomacy | Vassal armies controllable but may behave unpredictably | chat |
| 2026-11-01 | towns | Town founding enables trade; trade gives steep income growth; crafts give special products | chat |
| 2026-11-01 | map | Rivers end only at a lake or a confluence, never at the map edge | chat |
| 2026-11-01 | map | (superseded) 3–5 rivers per map (random); river tunables are module constants in `world.py` | chat |
| 2026-11-01 | map | Edge rivers: corner = 3 hexes meeting, edge = 2 hexes; Dijkstra with uphill penalty; max 30 edges | impl |
| 2026-11-01 | map | 5–9 rivers per map (random), longer; curvier on flat land; rivers may form islands | chat |
| 2026-11-01 | map | Meander = smooth noise field in the Dijkstra cost, stronger on flat terrain; islands = side channel round one flat hex; no river edges on the map border; rivers use their own RNG | impl |
