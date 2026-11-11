# 08 — Event / incident engine

`PROPOSED` One shared engine for: Church thresholds/demands, court petitions, feast and hunt
incidents, noble rebellions, the Church reform event, later succession.

## Sketch schema (data, not code)
```yaml
id: feast_drunken_brawl
source: feast            # court | feast | hunt | church | noble | world
trigger:                 # conditions evaluated at the action / turn start
  min_guests: 4
weight: 10               # relative probability among eligible events
actors: [host_province_count, random_guest]
choices:
  - label: "Punish the instigator"
    cost: { authority: 1 }
    effects: [ { target: random_guest, loyalty: -1 }, { target: host_province_count, loyalty: +1 } ]
  - label: "Laugh it off"
    effects: [ { target: realm, stability: -1 } ]
expires_in: 1            # turns the choice stays open
followups: []            # event ids that may be queued
```

## Notes
- Favours/grudges with expiry (04) are effects this engine writes.
- `DECIDED` Province **tension** (the gap between the Integration and Settlement meters, see 02)
  starts incidents by **weighted probability**, using the `weight` field, not at fixed thresholds.
  The weight can depend on the size of the gap.
- Keep it data-driven; designers (me) add events as YAML/JSON files.
