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

## Province organisation progression
- `PROPOSED` tribal territory → submission → conversion → **royal county** (appointed steward,
  2/3 of revenue to the crown) → **hereditary county** (autonomous).

## Entrenchment / rootedness meter
- `DECIDED` A count rootedness meter is important.
- `DECIDED` Hereditary status is **built up via the meter** (not given at start):
  Appointed → Settled → Embedded → Hereditary
  (Kinevezett → Megtelepedett → Beágyazott → Örökletes).
- `PROPOSED` Kindred monasteries (see 05) feed rootedness.
