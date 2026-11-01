# 04 — Nobility & diplomacy

## Starting situation
- `DECIDED` Game starts with the ruler and a few provinces: one is the ruler's own, the others are
  held by **tribal chiefs**, later organised into nobles.
- `DECIDED` Nobility starts as a **local loyalty modifier on province production**. Full
  representation `OPEN`. Burghers come later.

## Feudal graph
- `DECIDED` Simple **per-noble loyalty 1–5**. Low loyalty → won't join war, may rebel, needs
  punishing.
- `PROPOSED` Each noble has exactly **one liege**; war-call strength = product of loyalty factors
  along the chain. New knights automatically strengthen whoever their immediate lord is loyal to.
- `PROPOSED` Loyalty / stability / conversion all use one **converge-toward-target** model instead
  of fixed per-turn decay.
- `PROPOSED` Lightweight noble record: name, rank, loyalty, grudges/favours with expiry.
- `PROPOSED` Character traits: Loyal, Ambitious, Cautious, Greedy. `OPEN` how many for MVP.

## Unified relationship ladder
- `DECIDED` **One ladder for all political actors** (own nobles, tribal chiefs, counts,
  neighbouring kingdoms, city-states):
  **Hostile → Independent → Contractual → Tributary → Vassal (loyalty 1–5) → Annexed**
- `PROPOSED` Transition conditions/costs per step.
- `PROPOSED` Claims system: 0–3 claim per territory from dynastic ties, legal rulings, religious
  pretext.

## Marriage
- `DECIDED` Marriages handled **abstractly** for now.
- `PROPOSED` An abstract "dynastic bond" resource with inheritance-event hooks.

## Vassal armies
- `DECIDED` Vassals provide **controllable armies that may behave unpredictably**.
- `PROPOSED` Loyalty-based response table + feudal service duration limit + trait modifiers.
- `OPEN` Tie service duration to turn length?

## Idea pool — historical unification tools (Wessex, Franks, Capetians)
Burh/fortress networks · conversion with godparenthood ties · dynastic marriage · oath-taking ·
legal confiscation (Philip Augustus vs John, 1202) · purchase of territory · royal officials
(baillis) · town charters · apanage grants · shared law/identity. Use as a menu for ladder
transitions; none is committed.
