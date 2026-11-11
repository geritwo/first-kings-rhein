# 02 — Provinces & land

## Province structure
- `DECIDED` Provinces have **fixed borders**, even in unsettled areas.
- `DECIDED` A province = a **1-hex seat** (the count's estate) + **knight/baron estates** (1 hex each,
  expandable) + **common land** + an internal **wilderness ring**.
- `DECIDED` Provinces have **more than 7 hexes** (supersedes the earlier 7-hex layout:
  1 seat, 1 knight/clan chief, 5 common). Exact size `OPEN`.
- `DECIDED` The king's own province is **average**; his advantage comes only from royal actions.
- `DECIDED` True frontier zones (gyepű) exist **only at the realm's external edge**, between
  tribes/polities — not between the player's own provinces.

## Land ownership — per hex
- `DECIDED` Ownership is tracked **per hex**, not as province-level ratios.
- `PROPOSED` Owner types: crown, count, knight, church, town, common, wilderness.
- `OPEN` Default legal status of the wilderness ring: ownerless vs royal forest ban vs ecclesiastical.

## Knights
- `DECIDED` Knight estates **pay no tax and only add army**. They consume common land, so hexes run
  out and that limits knights — the constraint is built in.
- `PROPOSED` Two ways a knight appears:
  - *Organic* (province-built manor chain) → strengthens the count.
  - *Royal grant* during a court visit → strengthens the king, hurts the count's loyalty (eats the
    count's expansion land).
- `OPEN` Do inherited knights reset to base loyalty? Can a knight have two lords? (lean: no for MVP)

## Frontier expansion / internal colonisation (Landesausbau, Rodung)
- `DECIDED` Wants a mechanism for estates expanding toward the frontier.
- `DECIDED` Distant income-raising estates come via **land clearing + a local steward**.
  Development chain details `OPEN`.
- `PROPOSED` Clearing chain: wilderness → clearing → new village → developed village.
- `PROPOSED` Farmland chain: clearing → single-field → two-field → three-field rotation (+ watermill).

## Integration & Settlement (province meters)
- `DECIDED` Every province has two meters, tracked **per province** (not per hex; this is the one
  deliberate exception to hex-level granularity): **Integration** (the native population accepting
  the new rule) and **Settlement** (the incoming warrior class bound to the land). Integration has
  levels 0–5, Settlement 0–4.
- `DECIDED` Generic model, not Frank/Gaul-specific. Culture-specific names and levers live in data
  files. It applies to every province type: Roman-Gallic, tribal and own-culture.
- `DECIDED` Meters **only rise** (ratchet): no decay, no regression. Setbacks come from events
  (see 08), e.g. rebellion.
- `DECIDED` Where there is no incoming warrior class (e.g. the king's own province) Settlement is
  at its maximum from the start.
- `LEANING` The meters are *states*; buildings and actions are the *levers* that move them (the
  way kindred monasteries feed rootedness). Not a separate tech tree, not a pure building chain.
- `LEANING` **Tension** is derived from the gap between the two meters, not stored.
  `DECIDED` It triggers events with a **weighted probability** (the `weight` field in 08), not at
  fixed thresholds.
- `LEANING` Settlement level 3–4 unlocks creating knight estates (see Knights, F08).
- `PROPOSED` Integration levers: bishopric and bishop's palace (05), native vs. Frankish count,
  keeping Roman law and taxation, placitum events; for tribal provinces also hostages and
  godparenthood (see the idea pool in 04).
- `PROPOSED` Settlement levers: royal grants from fiscus land (the *royal grant* knight above),
  organised clearing (see Frontier expansion), manor and fort building.
- `PROPOSED` Starting values depend on province type (Roman-Gallic and tribal start low on
  Integration; own culture starts higher).
- `OPEN` Level names, lever costs and effects, starting values. Each lever gets the
  Opportunity / Constraint / Actor template when it is specced.

## Province organisation progression
- `DECIDED` The old single chain is **split in two** (2026-11-11):
  - The first steps, **tribal territory → submission → conversion**, are levels of the
    **Integration** meter above.
  - The count's legal position, **royal county** (appointed steward, 2/3 of revenue to the crown)
    → **hereditary county** (autonomous), is the **rootedness meter** below.
- `PROPOSED` Royal county and hereditary county details stay as in the original chain: appointed
  steward with 2/3 of revenue to the crown; autonomous once hereditary.

## Entrenchment / rootedness meter
- `DECIDED` A count rootedness meter is important.
- `DECIDED` Hereditary status is **built up via the meter** (not given at start):
  Appointed → Settled → Embedded → Hereditary
  (Kinevezett → Megtelepedett → Beágyazott → Örökletes).
- `PROPOSED` Kindred monasteries (see 05) feed rootedness.
- `PROPOSED` Hereditary status also needs a high **Integration** level (see above) on top of
  the rootedness steps.
