# 03 — Ruler & court

## The ruler on the map
- `DECIDED` The ruler is a **mobile map unit** with per-province actions.
- `DECIDED` The king is mechanically like any count (own average province) plus a **crown layer**
  of royal-only actions.
- `PROPOSED` Royal-only actions: grant land, issue charters, appoint stewards, call the banners.

## Itinerant economy
- `DECIDED` At start the ruler has **no income beyond his own province**; he must **travel to
  collect**. Staying in one place **depletes** that province.
- `DECIDED` Action costs depend on the **local biome economy**.
- `PROPOSED` A **Supply** stat, refilled in any province via:
  noble province (loyalty cost) / royal manor (building cost) / church institution (minor Church
  satisfaction cost).
- `PROPOSED` A dedicated **Authority** point, bound to the person (not dynastic) for now.

## Ruler actions
- `DECIDED` Actions include holding court, feasts, hunts; the rest still to be worked out.
- `DEFERRED` Tournaments (removed as anachronistic).
- `PROPOSED` details:
  - **Court / Judgment** — low risk. Generates 2–3 randomised noble petitions; each:
    fulfil / compromise / deny.
  - **Feast** — medium risk, wide but shallow impact across a guest list. Choices: pomp, guest
    list, seat of honour; plus an incident table.
  - **Hunt** — rare, narrow and deep impact on 1–2 companions; prey type (by biome) sets
    risk/reward; partial Supply refill on success.
- All three should run on the shared event engine (see 08).

## Succession
- `DEFERRED` Succession left out; possibly a random event later.
- `OPEN` What happens if the ruler dies before succession exists (incapacitation vs placeholder
  new-ruler event)?
