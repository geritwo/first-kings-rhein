"""
World / rules layer — provinces, settlement, buildings, seasons, resources.

No pygame in here: everything is plain Python so the rules can be tested and
simulated headless (see simulate.py).  The UI in main.py only reads this
state and calls the action methods.

Design summary (see the design notes in the project):
  * 1 turn = 1 season, 4 per year, starting 481 spring
  * province = the main unit; hexes inside it are wild / field / village /
    town quarter; the province grows by clearing adjacent wild hexes
  * one project slot per province (clearing OR a building step)
  * buildings are lines with upgrade tiers (earthwork -> palisade -> keep ...)
  * local resource: renders (stored per province, spoils, cannot travel)
  * global resources: silver, prestige (decays), authority/AU (capped)
  * loyalty: 4 discrete states; drifts down when the ruler stays away
  * the ruler is a unit on the map; where he stands, things happen
  * royal domain = direct orders; vassals act on their own traits unless
    you pay AU (or the ruler is present); independent tribes are AI
"""

import heapq
import math
import random

from hexcore import (SQRT3, DIRECTIONS, axial_to_pixel, corner_neighbors, corner_pixel, find_path,
                     flood_fill, hex_corner_keys, hex_distance, neighbors,
                     offset_to_axial, pixel_to_axial)

# ----------------------------------------------------------------------
# Time
# ----------------------------------------------------------------------
START_YEAR = 481
SEASONS = ["Tavasz", "Nyár", "Ősz", "Tél"]
SEASON_YIELD = [1.0, 1.0, 3.0, 0.0]     # autumn = harvest, winter = nothing
SEASON_WORK = [1.0, 1.0, 1.0, 0.5]      # building work per turn
SPOILAGE = 0.15                          # share of stored renders lost per season

# ----------------------------------------------------------------------
# Terrain: name, move cost (half-MP units: plains = 2), clear cost, clear turns
# move None = impassable, clear None = cannot be settled
# ----------------------------------------------------------------------
TERRAIN = {
    "plains":   dict(name="Síkság",  move=2, clear=4,  turns=2),
    "forest":   dict(name="Erdő",    move=3, clear=8,  turns=4),
    "hills":    dict(name="Dombság", move=3, clear=6,  turns=3),
    "marsh":    dict(name="Mocsár",  move=5, clear=10, turns=5),
    "mountain": dict(name="Hegység", move=None, clear=None, turns=None),
    "water":    dict(name="Tó",      move=None, clear=None, turns=None),
    "sea":      dict(name="Tenger",  move=None, clear=None, turns=None),
}
WATER = ("water", "sea")        # lake + sea

# Coast: one of these map sides always has sea along >= COAST_MIN_SHARE of its border
COAST_SIDES = ("west", "northwest", "north")
COAST_MIN_SHARE = 0.30
COAST_DROP = 0.45               # elevation lowered at the coastline ...
COAST_WIDTH = 3.0               # ... fading out over this many hexes (grown until the share is met)
COAST_BAY_AMP = 3.0             # hexes; noise on the coastline (bays, headlands)
REGION_TILT = 0.14              # land rises away from the coast (rivers drain to the sea)
SEA_LEVEL = 0.26
MOUNTAIN_ELEV = 0.72            # high ground above this is thinned to single-hex ridges
ROAD_MOVE = 1
TERRITORY_COST_IMPASSABLE = 5   # mountains/lakes can be claimed, not entered
TERRITORY_BUDGET = 4            # how far a province's claim reaches

# Rivers (F02): run along hex edges from hills/mountains to a lake or another river
RIVER_COUNT = (5, 9)            # random target count incl. major rivers, inclusive
RIVER_MAJOR_COUNT = 2           # Rhine/Loire-like: far highlands -> central plains -> sea
RIVER_MAJOR_FAR = 0.55          # majors rise beyond this share of the distance from the coast
RIVER_MAJOR_SPACING = 8         # min hex distance between major sources / between waypoints
RIVER_MAJOR_MAX_LEN = 160       # edges
RIVER_REPEL = 3.0               # extra step cost within a hex of an existing river (no parallel runs)
RIVER_CENTRE = (0.3, 0.7)       # central box (share of width and height) majors must pass
RIVER_MIN_LEN = 8               # edges; shorter rivers are rejected
RIVER_MAX_LEN = 70              # edges, minor rivers
RIVER_SOURCE_SPACING = 4        # min hex distance between river sources
RIVER_UPHILL_PENALTY = 20       # step cost per unit of climbed elevation (hills/mountains)
RIVER_UPHILL_FLAT = 6           # same on flat land: lets the meander channels win
RIVER_FLAT = ("plains", "forest", "marsh")   # terrain where rivers meander
RIVER_STEP_COST = 0.3           # base cost per edge; low = detours are cheap
RIVER_MEANDER_FLAT = 8.0        # extra step cost off the winding noise channels, flatlands
RIVER_MEANDER_HILL = 1.5        # same, hills/mountains (straighter, steeper courses)
RIVER_MEANDER_FREQ = 0.2        # channel noise frequency per hex; lower = wider loops
RIVER_WIGGLE_STEP = 7           # flat land: a meander waypoint every this many edges ...
RIVER_WIGGLE_AMP = 1.7          # ... pushed this many hexes to alternating sides of the course
RIVER_ISLAND_CHANCE = 0.5       # per river: a side channel round one flat hex

# Settlement level of a hex
WILD, FIELD, VILLAGE, TOWN = 0, 1, 2, 3
POP_NAMES = ["Vadon", "Szántó", "Falu", "Városnegyed"]
POP_RENDERS = [0, 1, 2, 2]
POP_SILVER = [0, 0, 0, 1]

# ----------------------------------------------------------------------
# Buildings: each line has tiers; one hex holds one line
# ----------------------------------------------------------------------
BUILDINGS = {
    "fort": dict(name="Vár", tiers=["Földvár", "Palánkvár", "Lakótorony", "Kővár"],
                 cost=[10, 25, 50, 90], turns=[2, 3, 5, 8],
                 min_pop=FIELD, unique=False, min_religion=0, royal_only=False),
    "church": dict(name="Egyház", tiers=["Fakápolna", "Templom", "Bazilika", "Katedrális"],
                   cost=[8, 25, 60, 120], turns=[2, 4, 8, 14],
                   min_pop=VILLAGE, unique=True, min_religion=0, royal_only=False),
    "monastery": dict(name="Kolostor", tiers=["Remeteség", "Kolostor", "Apátság"],
                      cost=[10, 30, 70], turns=[3, 5, 9],
                      min_pop=FIELD, unique=False, min_religion=1, royal_only=False),
    "market": dict(name="Piac", tiers=["Lerakat", "Piac", "Vásárhely"],
                   cost=[10, 30, 70], turns=[2, 4, 7],
                   min_pop=VILLAGE, unique=True, min_religion=0, royal_only=False),
    "pfalz": dict(name="Palota", tiers=["Királyi udvarház", "Palota"],
                  cost=[20, 60], turns=[3, 6],
                  min_pop=VILLAGE, unique=True, min_religion=0, royal_only=True),
}
TOWN_COST, TOWN_TURNS = 20, 4      # village -> town quarter
LINE_LIMIT = {"fort": lambda n: 1 + n // 4,      # n = settled hexes
              "monastery": lambda n: 1 + n // 8}
GROWTH_STORE, GROWTH_COST = 12, 6  # autumn: field -> village

RELIGION = ["Pogány", "Vegyes", "Keresztény"]
LOYALTY = ["Lázongó", "Bizalmatlan", "Hűséges", "Odaadó"]
LOYALTY_MULT = [0.5, 0.8, 1.0, 1.1]
ABSENCE_LIMIT = 8            # seasons without a royal visit -> loyalty -1
ABSENCE_LIMIT_PFALZ = 14
VASSAL_ORDER_AU = 3
AU_BASE, AU_CAP = 2, 20
FEAST_COST, FEAST_PRESTIGE = 10, 2
RULER_MP = 12                # half-MP units: 6 plains hexes, 12 on a road

TRAITS = ["Jámbor", "Becsvágyó", "Szorgos", "Harcias", "Rest", "Cselszövő"]

FACTIONS = {
    "player":  dict(name="Száli frankok", culture="frank", religion=0,
                    color=(196, 64, 52)),
    "frank":   dict(name="Frank kiskirály", culture="frank", religion=0,
                    color=(214, 150, 60)),
    "roman":   dict(name="Gallo-rómaiak", culture="roman", religion=2,
                    color=(150, 92, 168)),
    "alemann": dict(name="Alemannok", culture="alemann", religion=0,
                    color=(70, 120, 180)),
}

NAMES = {
    "frank": ["Tournai", "Cambrai", "Tongeren", "Köln", "Thérouanne", "Nijmegen",
              "Utrecht", "Maastricht", "Jülich", "Bonn", "Xanten", "Andernach"],
    "roman": ["Soissons", "Reims", "Laon", "Noyon", "Beauvais", "Amiens",
              "Senlis", "Châlons", "Troyes", "Párizs", "Meaux", "Arras"],
    "alemann": ["Breisgau", "Ortenau", "Thurgau", "Hegau", "Linzgau",
                "Klettgau", "Alpgau", "Baar", "Nagoldgau", "Zürichgau"],
}
LORDS = {
    "frank": ["Ragnachar", "Chararic", "Sigibert", "Rignomer", "Childebert",
              "Theudebald", "Ansoald", "Gundoald", "Chlodomer", "Audomar",
              "Baderic", "Sunno"],
    "roman": ["Syagrius", "Aurelianus", "Lupus", "Avitus", "Agrippinus",
              "Paulinus", "Ferreolus", "Ennodius", "Principius", "Volusianus",
              "Arbogastes", "Tonantius"],
    "alemann": ["Gibuld", "Hortar", "Vadomar", "Chnodomar", "Macrian",
                "Fraomar", "Gundomad", "Priarius", "Suomar", "Urius"],
}


# ----------------------------------------------------------------------
# Noise (value noise + fBm), pure Python
# ----------------------------------------------------------------------
def _hash01(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0x1000000)


def _value_noise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = _hash01(ix, iy, seed)
    b = _hash01(ix + 1, iy, seed)
    c = _hash01(ix, iy + 1, seed)
    d = _hash01(ix + 1, iy + 1, seed)
    top = a + (b - a) * sx
    bot = c + (d - c) * sx
    return top + (bot - top) * sy


def fbm(x, y, seed, octaves=4):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * _value_noise(x * freq, y * freq, seed + o * 101)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm


# ----------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------
class Tile:
    __slots__ = ("terrain", "pop", "province", "owner", "imp", "road",
                 "river", "col", "row")

    def __init__(self, terrain, col, row):
        self.terrain = terrain
        self.pop = WILD
        self.province = None   # who settled it (settled hexes only)
        self.owner = None      # territory owner (claim), incl. settled
        self.imp = None        # [line_key, tier_index] or None
        self.road = False
        self.river = False     # borders at least one river edge
        self.col, self.row = col, row


class Lord:
    def __init__(self, name, trait):
        self.name = name
        self.trait = trait


class Province:
    def __init__(self, pid, name, faction, seat, lord):
        self.id = pid
        self.name = name
        self.faction = faction        # key into FACTIONS
        self.status = "independent"   # 'royal' | 'vassal' | 'independent'
        self.seat = seat
        self.lord = lord
        self.store = 10.0             # renders, local
        self.loyalty = 2              # index into LOYALTY (player provinces)
        self.religion = FACTIONS[faction]["religion"]
        self.project = None           # dict, see World.start_*
        self.acted = False            # gave an order this turn
        self.last_visit = 0
        self.visit_streak = 0
        self.territory = set()
        self.settled = set()
        self.color = FACTIONS[faction]["color"]

    @property
    def is_player(self):
        return self.status in ("royal", "vassal")


class Ruler:
    def __init__(self, name, hex_pos, born):
        self.name = name
        self.hex = hex_pos
        self.born = born
        self.mp = RULER_MP


# ----------------------------------------------------------------------
# World
# ----------------------------------------------------------------------
class World:
    def __init__(self, width=40, height=28, seed=None, n_provinces=22):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.width, self.height = width, height
        self.tiles = {}
        self.provinces = []
        self.turn = 0
        self.silver = 5
        self.prestige = 10
        self.au = 6
        self.log = []
        self.rivers = []          # list of corner lists, source -> mouth
        self.n_major_rivers = 0   # rivers[:n] are the major ones
        self.river_branches = []  # side channels round an island hex
        self.river_edges = set()  # frozenset({hex_a, hex_b})
        self._generate_terrain()
        self._generate_rivers()
        self._place_provinces(n_provinces)
        self._build_roman_roads()
        self.recompute_territory()
        self.ruler = Ruler("Klodvig", self.capital.seat, born=466)
        self.add_log(f"{self.ruler.name}, a száli frankok királya, "
                     f"{self.capital.name} székhelyén trónra lép.")

    # ---- time helpers -------------------------------------------------
    @property
    def season(self):
        return self.turn % 4

    @property
    def year(self):
        return START_YEAR + self.turn // 4

    def date_str(self, turn=None):
        t = self.turn if turn is None else turn
        return f"{START_YEAR + t // 4} {SEASONS[t % 4].lower()}"

    def add_log(self, text):
        self.log.append(f"{self.date_str()}: {text}")
        self.log = self.log[-60:]

    # ---- generation ---------------------------------------------------
    def _coast_distance(self, x, y):
        """Distance in hexes from the coast side (pixel coords at size 1)."""
        if self.coast_side == "west":
            return x / SQRT3
        if self.coast_side == "north":
            return y / SQRT3
        return (x + y) / math.sqrt(2) / SQRT3        # northwest: from the corner

    def _coast_border(self, col, row):
        """Is this hex on the map border of the coast side?"""
        if self.coast_side == "west":
            return col == 0
        if self.coast_side == "north":
            return row == 0
        return (col == 0 and row < self.height * 0.6) or (row == 0 and col < self.width * 0.6)

    def _generate_terrain(self):
        s = self.seed
        self.coast_side = random.Random(s * 7919 + 1).choice(COAST_SIDES)
        base, moist, dist, border = {}, {}, {}, []
        for row in range(self.height):
            for col in range(self.width):
                h = offset_to_axial(col, row)
                x, y = axial_to_pixel(*h, 1.0)
                base[h] = fbm(x * 0.09, y * 0.09, s)
                m = fbm(x * 0.11 + 50, y * 0.11 + 50, s + 7)
                # east = Germania (forest), west = Gaul (open, farmed)
                moist[h] = m + (col / self.width - 0.5) * 0.35
                bay = (fbm(x * 0.12 + 20, y * 0.12 + 20, s + 31) - 0.5) * 2 * COAST_BAY_AMP
                dist[h] = (self._coast_distance(x, y), bay, col, row)
                if self._coast_border(col, row):
                    border.append(h)
        dmax = max(d for d, _, _, _ in dist.values())

        def elevations(width):
            return {h: base[h] + REGION_TILT * (d / dmax - 0.5)
                    - COAST_DROP * max(0.0, 1 - (d + bay) / width)
                    for h, (d, bay, _, _) in dist.items()}

        def sea_from(elev):
            sea = {h for h in border if elev[h] < SEA_LEVEL}
            stack = list(sea)
            while stack:
                for n in neighbors(stack.pop()):
                    if n in elev and n not in sea and elev[n] < SEA_LEVEL:
                        sea.add(n)
                        stack.append(n)
            return sea

        width = COAST_WIDTH
        while True:     # widen the coastal lowland until enough of the border is sea
            self.elev = elevations(width)
            sea = sea_from(self.elev)
            if sum(h in sea for h in border) >= COAST_MIN_SHARE * len(border):
                break
            width += 0.5

        for h, (_, _, col, row) in dist.items():
            e, m = self.elev[h], moist[h]
            if h in sea:
                t = "sea"
            elif e > MOUNTAIN_ELEV:
                t = "mountain"
            elif e > 0.61:
                t = "hills"
            elif e < SEA_LEVEL:
                t = "water"
            elif m > 0.72 and e < 0.42:
                t = "marsh"
            elif m > 0.52:
                t = "forest"
            else:
                t = "plains"
            self.tiles[h] = Tile(t, col, row)
        self._thin_mountains()

    def _thin_mountains(self):
        """Peel mountain blobs down to single-hex ridges along their highest
        line; peeled hexes become hills (foothills).  A hex is peeled when
        its mountain neighbours form one contiguous arc of 2-5 hexes: it sits
        in a 2-wide band, and removing it neither splits the ridge nor
        shortens a ridge end.  Junctions of ridges may stay 2 wide."""
        mtn = {h for h, t in self.tiles.items() if t.terrain == "mountain"}
        changed = True
        while changed:
            changed = False
            for h in sorted(mtn, key=lambda h: (self.elev[h], h)):
                ring = [n in mtn for n in neighbors(h)]
                count = sum(ring)
                arcs = sum(1 for i in range(6) if ring[i] and not ring[i - 1])
                if arcs == 1 and 2 <= count <= 5:
                    mtn.discard(h)
                    self.tiles[h].terrain = "hills"
                    changed = True

    def _generate_rivers(self):
        """Edge rivers: Dijkstra over the hex-corner graph, from a high corner
        downhill to a corner touching a lake or an earlier river.  A smooth
        noise field (stronger on flat land) bends the course; some rivers get
        a side channel round one hex, which becomes an island."""
        # own RNG: river tuning must not reshuffle provinces etc. on a given seed
        rng = random.Random(self.seed * 7919 + 2)

        def on_map(c):
            return [h for h in c if h in self.tiles]

        def touches_water(c):
            return any(self.tiles[h].terrain in WATER for h in on_map(c))

        elev_cache = {}

        def elev(c):
            if c not in elev_cache:
                hs = on_map(c)
                elev_cache[c] = sum(self.elev[h] for h in hs) / len(hs)
            return elev_cache[c]

        meander_cache, nbr_cache = {}, {}

        def meander(c, field):
            key = (c, field)
            if key not in meander_cache:
                x, y = corner_pixel(c, 1.0)
                f = RIVER_MEANDER_FREQ / SQRT3          # per hex, not per unit
                # winding channels: the 0.5-contour of the noise field costs nothing
                meander_cache[key] = abs(2 * fbm(x * f, y * f, field, octaves=2) - 1)
            return meander_cache[key]

        def corner_nbrs(c):
            if c not in nbr_cache:
                nbr_cache[c] = [(e, n, all(h in self.tiles for h in e)
                                 and all(self.tiles[h].terrain in RIVER_FLAT for h in e))
                                for e, n in corner_neighbors(c)
                                if all(h in self.tiles for h in e)]  # not along the border
            return nbr_cache[c]

        def step_cost(c1, flat, c2, field):
            amp = RIVER_MEANDER_FLAT if flat else RIVER_MEANDER_HILL
            uphill = RIVER_UPHILL_FLAT if flat else RIVER_UPHILL_PENALTY
            return (RIVER_STEP_COST
                    + uphill * max(0.0, elev(c2) - elev(c1))
                    + amp * meander(c2, field))

        def touches_sea(c):
            return any(self.tiles[h].terrain == "sea" for h in on_map(c))

        river_corners = set()

        def near_river(c):
            """Within a hex of an existing river (corner touches a river hex)."""
            return any(self.tiles[h].river for h in on_map(c))

        def dijkstra(source, is_goal, blocked, field, repel=False):
            """Cheapest corner path from source to the first goal corner."""
            dist, prev = {source: 0.0}, {source: None}
            heap, tie = [(0.0, 0, source)], 1
            while heap:
                d, _, c = heapq.heappop(heap)
                if d > dist[c]:
                    continue
                if c != source and is_goal(c):
                    path = []
                    while c is not None:
                        path.append(c)
                        c = prev[c]
                    return path[::-1]
                for _, n, flat in corner_nbrs(c):
                    if blocked(n) and not is_goal(n):
                        continue
                    nd = d + step_cost(c, flat, n, field)
                    if repel and near_river(n):
                        nd += RIVER_REPEL           # don't hug another river
                    if nd < dist.get(n, math.inf):
                        dist[n], prev[n] = nd, c
                        heapq.heappush(heap, (nd, tie, n))
                        tie += 1
            return None

        def path_from(source, field):
            return dijkstra(source, lambda c: c in river_corners or touches_water(c),
                            lambda c: False, field, repel=True)

        def add_course(path):
            river_corners.update(path)
            for c1, c2 in zip(path, path[1:]):
                edge = c1 & c2
                self.river_edges.add(edge)
                for h in edge:
                    if h in self.tiles:
                        self.tiles[h].river = True

        def island_branch(path):
            """A side channel round a flat hex the river already runs along
            for 2-3 edges: the other side of that hex, from where the river
            meets it to where it leaves it."""
            options = []
            for i in range(len(path) - 2):
                shared = path[i] & path[i + 1] & path[i + 2]
                if len(shared) != 1:
                    continue
                h = next(iter(shared))
                if (h not in self.tiles or self.tiles[h].terrain not in RIVER_FLAT
                        or any(n not in self.tiles for n in neighbors(h))):
                    continue
                j = i + 2
                if j + 1 < len(path) and h in path[j + 1]:
                    j += 1                      # runs along 3 edges of h
                if i > 0 and h in path[i - 1]:
                    continue                    # counted from its first corner only
                ring = hex_corner_keys(h)
                k0, k1 = ring.index(path[i]), ring.index(path[j])
                inner = set(path[i + 1:j])
                arcs = ([ring[(k0 + s) % 6] for s in range(7) if s <= (k1 - k0) % 6],
                        [ring[(k0 - s) % 6] for s in range(7) if s <= (k0 - k1) % 6])
                branch = next(a for a in arcs if not inner & set(a))
                mids = branch[1:-1]
                if any(c in river_corners or touches_water(c) for c in mids):
                    continue
                options.append(branch)
            return rng.choice(options) if options else None

        # sources: mountain corners first, then hills; highest first
        candidates = {}
        for h, t in self.tiles.items():
            if t.terrain in ("mountain", "hills"):
                rank = 0 if t.terrain == "mountain" else 1
                for c in hex_corner_keys(h):
                    if len(on_map(c)) == 3 and not touches_water(c):
                        candidates[c] = min(candidates.get(c, 9), rank)
        order = sorted(candidates, key=lambda c: (candidates[c], -elev(c),
                                                  sorted(c)))
        def is_flat(c):
            return len(on_map(c)) == 3 and all(self.tiles[h].terrain in RIVER_FLAT for h in c)

        def nearest_corner(x, y):
            h = pixel_to_axial(x, y, 1.0)
            cs = [c for n in [h, *neighbors(h)] for c in hex_corner_keys(n)]
            return min(cs, key=lambda c: ((corner_pixel(c, 1.0)[0] - x) ** 2
                                          + (corner_pixel(c, 1.0)[1] - y) ** 2, sorted(c)))

        def meandered(path, field, keep=()):
            """Bend flat stretches: waypoints every RIVER_WIGGLE_STEP edges,
            pushed to alternating sides, then re-routed through. Corners in
            `keep` (e.g. a major river's central waypoint) stay on the course.
            Falls back to the original path if any leg can't be routed."""
            k = RIVER_WIGGLE_STEP
            marks = sorted({0, len(path) - 1}
                           | set(range(k, len(path) - k // 2, k))
                           | {path.index(c) for c in keep})
            side = rng.choice((-1, 1))
            waypoints = []
            for i in marks:
                c = path[i]
                if 0 < i < len(path) - 1 and c not in keep and is_flat(c):
                    (ax, ay), (bx, by) = (corner_pixel(path[max(0, i - k)], 1.0),
                                          corner_pixel(path[min(len(path) - 1, i + k)], 1.0))
                    dx, dy = bx - ax, by - ay
                    norm = math.hypot(dx, dy) or 1.0
                    off = side * RIVER_WIGGLE_AMP * SQRT3 * rng.uniform(0.6, 1.3)
                    x, y = corner_pixel(c, 1.0)
                    t = nearest_corner(x - dy / norm * off, y + dx / norm * off)
                    if (is_flat(t) and not touches_water(t) and t not in river_corners
                            and t not in waypoints):
                        c = t
                    side = -side
                if c not in waypoints:
                    waypoints.append(c)
            out = [waypoints[0]]
            used = {waypoints[0]}
            for a, b in zip(waypoints, waypoints[1:]):
                if b in used:
                    return path
                leg = dijkstra(a, lambda c, b=b: c == b,
                               lambda c: (c in used or c in waypoints or c in river_corners
                                          or touches_water(c)),
                               field, repel=True)
                if leg is None:
                    return path
                out += leg[1:]
                used.update(leg)
            return out

        def finish(path):
            self.rivers.append(path)
            add_course(path)
            if rng.random() < RIVER_ISLAND_CHANCE:
                branch = island_branch(path)
                if branch:
                    self.river_branches.append(branch)
                    add_course(branch)

        target = rng.randint(*RIVER_COUNT)
        sources = []

        # major rivers: rise far from the coast, pass a central flat corner, reach the sea
        def coast_dist(c):
            return sum(self._coast_distance(*axial_to_pixel(*h, 1.0)) for h in c) / 3

        dmax = max(coast_dist(c) for c in candidates)
        far = [c for c in order if coast_dist(c) >= RIVER_MAJOR_FAR * dmax]
        # fallback when the far side has few hills: its highest land corners
        far += sorted({c for h in self.tiles for c in hex_corner_keys(h)
                       if len(on_map(c)) == 3 and not touches_water(c)
                       and c not in candidates
                       and coast_dist(c) >= RIVER_MAJOR_FAR * dmax},
                      key=lambda c: (-elev(c), sorted(c)))
        lo, hi = RIVER_CENTRE
        centre = sorted({c for h, t in self.tiles.items()
                         if lo * self.width <= t.col <= hi * self.width
                         and lo * self.height <= t.row <= hi * self.height
                         for c in hex_corner_keys(h)
                         if len(on_map(c)) == 3
                         and all(self.tiles[x].terrain in RIVER_FLAT for x in c)},
                        key=sorted)
        waypoints = []
        for src in far:
            if len(self.rivers) >= RIVER_MAJOR_COUNT:
                break
            if src in river_corners:
                continue
            if any(hex_distance(a, b) < RIVER_MAJOR_SPACING
                   for s in sources for a in src for b in s):
                continue
            field = self.seed + 1000 + 17 * len(sources)
            options = {w for w in centre if w not in river_corners
                       and all(hex_distance(a, b) >= RIVER_MAJOR_SPACING
                               for p in waypoints for a in w for b in p)}
            for _try in range(3):           # nearest reachable central corner first
                leg1 = dijkstra(src, lambda c: c in options,
                                lambda c: c in river_corners or touches_water(c), field,
                                repel=True)
                if leg1 is None:
                    break
                wp, used = leg1[-1], set(leg1)
                leg2 = dijkstra(wp, touches_sea,
                                lambda c: c in used or c in river_corners or touches_water(c),
                                field, repel=True)
                if leg2 is None:
                    options.discard(wp)
                    continue
                path = leg1 + leg2[1:]
                if len(path) - 1 <= RIVER_MAJOR_MAX_LEN:
                    sources.append(src)
                    waypoints.append(wp)
                    finish(meandered(path, field, keep=(wp,)))
                break
        self.n_major_rivers = len(self.rivers)

        for src in order:
            if len(self.rivers) >= target:
                break
            if src in river_corners:
                continue
            if any(hex_distance(a, b) < RIVER_SOURCE_SPACING
                   for s in sources for a in src for b in s):
                continue
            field = self.seed + 1000 + 17 * len(sources)   # own bends per river
            path = path_from(src, field)
            if path is None or not (RIVER_MIN_LEN <= len(path) - 1 <= RIVER_MAX_LEN):
                continue
            sources.append(src)
            finish(meandered(path, field))

    def is_river_edge(self, a, b):
        """True if a river runs between neighbouring hexes a and b."""
        return frozenset((a, b)) in self.river_edges

    def _region(self, col, row):
        if col < self.width * 0.40 and row > self.height * 0.30:
            return "roman"
        if col > self.width * 0.60 and row > self.height * 0.50:
            return "alemann"
        return "frank"

    def _place_provinces(self, n):
        candidates = [h for h, t in self.tiles.items()
                      if t.terrain in ("plains", "hills")
                      and 1 <= t.col < self.width - 1 and 1 <= t.row < self.height - 1]
        self.rng.shuffle(candidates)
        seats = []
        for h in candidates:
            if all(hex_distance(h, s) >= 6 for s in seats):
                seats.append(h)
            if len(seats) >= n:
                break

        names = {k: v[:] for k, v in NAMES.items()}
        lords = {k: v[:] for k, v in LORDS.items()}
        for lst in list(names.values()) + list(lords.values()):
            self.rng.shuffle(lst)

        for i, seat in enumerate(seats):
            t = self.tiles[seat]
            fac = self._region(t.col, t.row)
            name = names[fac].pop() if names[fac] else f"{fac}-{i}"
            lord = Lord(lords[fac].pop() if lords[fac] else "Ismeretlen",
                        self.rng.choice(TRAITS))
            p = Province(i, name, fac, seat, lord)
            self.provinces.append(p)

        # the player: frank seat nearest the north-centre, plus its 2 nearest
        # frank neighbours as royal domain and the next one as a vassal
        target = offset_to_axial(int(self.width * 0.5), int(self.height * 0.30))
        franks = [p for p in self.provinces if p.faction == "frank"]
        home = min(franks, key=lambda p: hex_distance(p.seat, target))
        others = sorted((p for p in franks if p is not home),
                        key=lambda p: hex_distance(p.seat, home.seat))
        for p in [home] + others[:2]:
            p.faction, p.status = "player", "royal"
            p.color = FACTIONS["player"]["color"]
        if len(others) > 2:
            v = others[2]
            v.faction, v.status = "player", "vassal"
            v.color = FACTIONS["player"]["color"]
        home.lord = Lord("Klodvig", "Becsvágyó")
        self.capital = home

        # vary colours a little per province so neighbours stand apart
        for p in self.provinces:
            if not p.is_player:
                j = self.rng.randint(-22, 22)
                p.color = tuple(max(0, min(255, c + j)) for c in p.color)

        # starting settlement
        for p in self.provinces:
            roman = p.faction == "roman"
            seat_tile = self.tiles[p.seat]
            self._settle(p.seat, p, TOWN if roman else VILLAGE)
            seat_tile.imp = ["fort", 0]
            ring = [n for n in neighbors(p.seat)
                    if n in self.tiles and self._clearable(n)
                    and self.tiles[n].province is None]
            self.rng.shuffle(ring)
            for k, n in enumerate(ring[: (4 if roman else 3)]):
                self._settle(n, p, VILLAGE if (roman and k == 0) else FIELD)
            if roman:
                p.store = 18.0
                spots = [h for h in ring[:4] if self.tiles[h].pop >= VILLAGE]
                if spots:
                    self.tiles[spots[0]].imp = ["church", 1]
                else:
                    seat_tile.imp = ["church", 1]
            if p.is_player:
                p.store = 20.0
            p.last_visit = 0

    def _settle(self, h, p, level):
        t = self.tiles[h]
        t.pop = level
        t.province = p
        t.owner = p
        p.settled.add(h)
        p.territory.add(h)

    def _build_roman_roads(self):
        romans = [p for p in self.provinces if p.faction == "roman"]

        def cost(a, b):
            if b not in self.tiles:
                return None
            return TERRAIN[self.tiles[b].terrain]["move"]

        done = set()
        for p in romans:
            others = sorted((q for q in self.provinces if q is not p),
                            key=lambda q: hex_distance(p.seat, q.seat))
            # link to the nearest roman city and to one non-roman neighbour
            targets = [q for q in others if q.faction == "roman"][:1]
            targets += [q for q in others if q.faction != "roman"][:1]
            for q in targets:
                key = frozenset((p.id, q.id))
                if key in done:
                    continue
                done.add(key)
                path, _ = find_path(p.seat, q.seat, cost, min_step=2)
                if path:
                    for h in path:
                        self.tiles[h].road = True

    # ---- queries ------------------------------------------------------
    def _clearable(self, h):
        t = self.tiles.get(h)
        return t is not None and TERRAIN[t.terrain]["clear"] is not None

    def move_cost(self, a, b):
        """Step cost for units (half-MP units), None = impassable."""
        tb = self.tiles.get(b)
        if tb is None:
            return None
        if tb.road and self.tiles[a].road:
            return ROAD_MOVE
        return TERRAIN[tb.terrain]["move"]

    def _territory_cost(self, a, b):
        tb = self.tiles.get(b)
        if tb is None:
            return None
        m = TERRAIN[tb.terrain]["move"]
        return TERRITORY_COST_IMPASSABLE if m is None else m

    def province_at(self, h):
        t = self.tiles.get(h)
        return t.owner if t else None

    def player_provinces(self):
        return [p for p in self.provinces if p.is_player]

    def ruler_province(self):
        return self.province_at(self.ruler.hex)

    def ruler_present(self, p):
        return self.ruler_province() is p

    def recompute_territory(self):
        sources = {}
        for h, t in self.tiles.items():
            if t.province is not None:
                sources[h] = (0, t.province)
        # project hexes (clearing in progress) also anchor the claim
        for p in self.provinces:
            if p.project and p.project["kind"] == "clear":
                sources.setdefault(p.project["hex"], (0, p))
        result = flood_fill(sources, self._territory_cost, TERRITORY_BUDGET)
        for t in self.tiles.values():
            t.owner = None
        for p in self.provinces:
            p.territory = set()
            p.settled = set()
        for h, (_, p) in result.items():
            if h in self.tiles:
                self.tiles[h].owner = p
                p.territory.add(h)
        for h, t in self.tiles.items():
            if t.province is not None:
                t.owner = t.province
                t.province.territory.add(h)
                t.province.settled.add(h)

    def knights(self, p):
        """Castles raise knights: sum of fort tiers in the province."""
        return sum(self.tiles[h].imp[1] + 1 for h in p.settled
                   if self.tiles[h].imp and self.tiles[h].imp[0] == "fort")

    def has_line(self, p, line):
        return any(self.tiles[h].imp and self.tiles[h].imp[0] == line
                   for h in p.settled)

    def count_line(self, p, line):
        return sum(1 for h in p.settled
                   if self.tiles[h].imp and self.tiles[h].imp[0] == line)

    def labour(self, p):
        """Work done per season: bigger provinces build faster (0.6 .. 2.0)."""
        return max(0.6, min(2.0, 0.6 + 0.1 * len(p.settled)))

    def best_tier(self, p, line):
        tiers = [self.tiles[h].imp[1] for h in p.settled
                 if self.tiles[h].imp and self.tiles[h].imp[0] == line]
        return max(tiers) if tiers else -1

    def loyalty_floor(self, p):
        return 1 if self.best_tier(p, "church") >= 1 else 0

    def yields(self, p):
        """Base per-season yield before the season multiplier: (renders, silver)."""
        renders, silver = 0.0, 0.0
        for h in p.settled:
            t = self.tiles[h]
            renders += POP_RENDERS[t.pop] + (1 if t.river and t.pop else 0)
            silver += POP_SILVER[t.pop]
            if t.imp:
                line, tier = t.imp
                if line == "monastery":
                    renders += tier + 1
                elif line == "market":
                    silver += tier + 1 + (1 if t.road else 0)
        if p.is_player:
            renders *= LOYALTY_MULT[p.loyalty]
        return renders, silver

    def au_income(self):
        inc = AU_BASE
        for p in self.player_provinces():
            tier = self.best_tier(p, "church")
            inc += {1: 1, 2: 2, 3: 2}.get(tier, 0)   # templom, püspökség
            if self.best_tier(p, "pfalz") >= 0:
                inc += 1
        return inc

    # ---- orders -------------------------------------------------------
    def can_order(self, p):
        """(ok, reason, au_cost) — may the player give this province an order?"""
        if not p.is_player:
            return False, "Idegen tartomány", 0
        if p.acted:
            return False, "Ebben a körben már kapott parancsot", 0
        if p.status == "vassal" and not self.ruler_present(p):
            if self.au < VASSAL_ORDER_AU:
                return False, f"Vazallus: {VASSAL_ORDER_AU} tekintély kell", VASSAL_ORDER_AU
            return True, f"Vazallus: {VASSAL_ORDER_AU} tekintélybe kerül", VASSAL_ORDER_AU
        return True, "", 0

    def _pay_order(self, p):
        ok, _, au = self.can_order(p)
        if not ok:
            return False
        self.au -= au
        p.acted = True
        return True

    def clear_targets(self, p):
        if p.project:
            return set()
        out = set()
        for h in p.territory:
            t = self.tiles[h]
            if t.pop != WILD or not self._clearable(h):
                continue
            if any(self.provinces_project_hex(h)):
                continue
            if any(n in p.settled for n in neighbors(h)):
                out.add(h)
        return out

    def provinces_project_hex(self, h):
        return [q for q in self.provinces if q.project and q.project["hex"] == h]

    def clear_cost(self, p, h):
        terr = TERRAIN[self.tiles[h].terrain]
        turns = terr["turns"]
        if self.has_line(p, "monastery"):
            turns = max(1, turns - 1)
        return terr["clear"], turns

    def build_options(self, p, h):
        """List of dicts describing what can be built on hex h."""
        t = self.tiles.get(h)
        if t is None or h not in p.settled:
            return []
        opts = []
        if t.imp:
            line, tier = t.imp
            b = BUILDINGS[line]
            if tier + 1 < len(b["tiers"]):
                opts.append(self._option(p, line, tier + 1, h))
        else:
            for line, b in BUILDINGS.items():
                if t.pop < b["min_pop"]:
                    continue
                if b["unique"] and self.has_line(p, line):
                    continue
                if line in LINE_LIMIT and self.count_line(p, line) >= LINE_LIMIT[line](len(p.settled)):
                    continue
                if b["royal_only"] and p.status != "royal":
                    continue
                opts.append(self._option(p, line, 0, h))
            if t.pop == VILLAGE and self._town_ok(p, h):
                opts.append(dict(kind="town", line=None, tier=None,
                                 label="Városnegyed", cost=TOWN_COST,
                                 turns=TOWN_TURNS,
                                 ok=p.store >= TOWN_COST,
                                 reason="" if p.store >= TOWN_COST else "Kevés a szolgáltatás"))
        return opts

    def _town_ok(self, p, h):
        for n in neighbors(h):
            if n == p.seat:
                return True
            tn = self.tiles.get(n)
            if tn and tn.province is p and (tn.pop == TOWN or (tn.imp and tn.imp[1] >= 1)):
                return True
        return False

    def _option(self, p, line, tier, h):
        b = BUILDINGS[line]
        cost, turns = b["cost"][tier], b["turns"][tier]
        ok, reason = True, ""
        if p.religion < b["min_religion"]:
            ok, reason = False, "Keresztény vagy vegyes vallás kell"
        elif p.store < cost:
            ok, reason = False, "Kevés a szolgáltatás"
        return dict(kind="build", line=line, tier=tier, label=b["tiers"][tier],
                    cost=cost, turns=turns, ok=ok, reason=reason)

    def build_targets(self, p):
        if p.project:
            return set()
        return {h for h in p.settled if self.build_options(p, h)}

    def start_clear(self, p, h, by_player=True):
        if h not in self.clear_targets(p):
            return False
        cost, turns = self.clear_cost(p, h)
        if p.store < cost:
            return False
        if by_player and not self._pay_order(p):
            return False
        p.store -= cost
        p.project = dict(kind="clear", hex=h, label="Irtás", left=float(turns),
                         total=turns)
        if by_player:
            self.recompute_territory()   # NPC claims are refreshed at turn end
        return True

    def start_build(self, p, h, opt, by_player=True):
        if p.project or not opt["ok"]:
            return False
        if by_player and not self._pay_order(p):
            return False
        p.store -= opt["cost"]
        p.project = dict(kind=opt["kind"], hex=h, line=opt["line"],
                         tier=opt["tier"], label=opt["label"],
                         left=float(opt["turns"]), total=opt["turns"])
        return True

    def can_feast(self, p):
        if not self.ruler_present(p):
            return False, "Csak a király jelenlétében"
        if p.store < FEAST_COST:
            return False, "Kevés a szolgáltatás"
        ok, reason, _ = self.can_order(p)
        if not ok:
            return False, reason
        return True, ""

    def feast(self, p):
        ok, _ = self.can_feast(p)
        if not ok or not self._pay_order(p):
            return False
        p.store -= FEAST_COST
        self.prestige += FEAST_PRESTIGE
        if p.loyalty < 3:
            p.loyalty += 1
        self.add_log(f"Lakoma {p.name} csarnokában. Presztízs +{FEAST_PRESTIGE}, "
                     f"{p.lord.name} hűsége: {LOYALTY[p.loyalty]}.")
        return True

    # ---- ruler movement ----------------------------------------------
    def ruler_reachable(self):
        res = flood_fill({self.ruler.hex: (0, None)}, self.move_cost, self.ruler.mp)
        return {h: c for h, (c, _) in res.items() if h != self.ruler.hex}

    def ruler_path(self, goal):
        return find_path(self.ruler.hex, goal, self.move_cost, min_step=ROAD_MOVE)

    def move_ruler(self, goal):
        path, cost = self.ruler_path(goal)
        if path is None or cost > self.ruler.mp:
            return None
        self.ruler.mp -= cost
        self.ruler.hex = goal
        return path

    # ---- NPC lords ----------------------------------------------------
    def _npc_act(self, p):
        if p.project:
            return
        trait = p.lord.trait
        if trait == "Rest" and self.rng.random() < 0.5:
            return
        weights = {"clear": 2, "fort": 1, "church": 1, "monastery": 1,
                   "market": 1, "town": 1, "pfalz": 0}
        if trait == "Jámbor":
            weights.update(church=5, monastery=4)
        elif trait in ("Harcias", "Becsvágyó"):
            weights.update(fort=4, clear=3)
        elif trait == "Szorgos":
            weights.update(clear=4, market=3, town=2)
        elif trait == "Cselszövő":
            weights.update(market=3)
        if p.religion == 0 and p.faction != "roman":
            weights["church"] = weights["church"] * 0.3  # pagan lords hesitate

        choices = []
        for h in self.clear_targets(p):
            cost, _ = self.clear_cost(p, h)
            if p.store >= cost:
                choices.append((weights["clear"] / 3, ("clear", h, None)))
        for h in p.settled:
            for opt in self.build_options(p, h):
                if opt["ok"]:
                    key = "town" if opt["kind"] == "town" else opt["line"]
                    w = weights.get(key, 1)
                    if w > 0:
                        choices.append((w, ("build", h, opt)))
        if not choices:
            return
        total = sum(w for w, _ in choices)
        pick = self.rng.random() * total
        for w, (kind, h, opt) in choices:
            pick -= w
            if pick <= 0:
                break
        if kind == "clear":
            self.start_clear(p, h, by_player=False)
        else:
            self.start_build(p, h, opt, by_player=False)
            if p.status == "vassal":
                self.add_log(f"{p.lord.name} ({p.name}) saját döntésből: {opt['label']}.")

    # ---- turn resolution -----------------------------------------------
    def end_turn(self):
        season = self.season

        # 1. lords who were not given an order act on their own
        for p in self.provinces:
            if p.status == "independent" or (p.status == "vassal" and not p.acted):
                self._npc_act(p)

        # 2. projects advance
        for p in self.provinces:
            if not p.project:
                continue
            p.project["left"] -= SEASON_WORK[season] * self.labour(p)
            if p.project["left"] <= 0:
                self._complete(p)

        # 3. production, spoilage, global income
        for p in self.provinces:
            renders, silver = self.yields(p)
            p.store += renders * SEASON_YIELD[season]
            p.store *= (1 - SPOILAGE)
            if p.is_player:
                self.silver += silver
        self.au = min(AU_CAP, self.au + self.au_income())

        # 4. autumn growth: a field next to a village or the seat grows
        if season == 2:
            for p in self.provinces:
                if p.store < GROWTH_STORE:
                    continue
                fields = sum(1 for h in p.settled if self.tiles[h].pop == FIELD)
                villages = sum(1 for h in p.settled
                               if self.tiles[h].pop >= VILLAGE and h != p.seat)
                if fields < villages + 2:      # a village needs fields around it
                    continue
                cands = [h for h in p.settled if self.tiles[h].pop == FIELD
                         and any(n == p.seat or (n in p.settled and self.tiles[n].pop >= VILLAGE)
                                 for n in neighbors(h))]
                if cands:
                    h = self.rng.choice(sorted(cands))
                    self.tiles[h].pop = VILLAGE
                    p.store -= GROWTH_COST
                    if p.is_player:
                        self.add_log(f"{p.name}: új falu nőtt ki a szántók közül.")

        # 5. loyalty: the ruler's visit lifts it, long absence wears it down
        rp = self.ruler_province()
        for p in self.player_provinces():
            if p is rp:
                if p.visit_streak == 0 and p.loyalty < 2:
                    p.loyalty += 1
                    self.add_log(f"A király {p.name} tartományban időzik; "
                                 f"{p.lord.name} hűsége: {LOYALTY[p.loyalty]}.")
                p.visit_streak += 1
                p.last_visit = self.turn
            else:
                p.visit_streak = 0
                limit = ABSENCE_LIMIT_PFALZ if self.best_tier(p, "pfalz") >= 0 else ABSENCE_LIMIT
                if self.turn - p.last_visit >= limit:
                    floor = self.loyalty_floor(p)
                    if p.loyalty > floor:
                        p.loyalty -= 1
                        self.add_log(f"{p.name} rég nem látta a királyt: "
                                     f"{p.lord.name} hűsége: {LOYALTY[p.loyalty]}.")
                    p.last_visit = self.turn   # restart the clock

        # 6. advance time
        self.turn += 1
        if self.season == 0:
            if self.prestige > 0:
                self.prestige -= 1
            self.add_log(f"Új esztendő. A tettek nélküli presztízs kopik (-1).")
        for p in self.provinces:
            p.acted = False
        self.ruler.mp = RULER_MP
        self.recompute_territory()

    def _complete(self, p):
        pr = p.project
        h = pr["hex"]
        t = self.tiles[h]
        p.project = None
        if pr["kind"] == "clear":
            self._settle(h, p, FIELD)
            msg = f"{p.name}: az irtás elkészült, új szántó ({TERRAIN[t.terrain]['name'].lower()})."
        elif pr["kind"] == "town":
            t.pop = TOWN
            msg = f"{p.name}: új városnegyed."
        else:
            line, tier = pr["line"], pr["tier"]
            t.imp = [line, tier]
            msg = f"{p.name}: elkészült — {pr['label']}."
            n_tiers = len(BUILDINGS[line]["tiers"])
            if p.is_player and tier >= 2:
                gain = 6 if tier == n_tiers - 1 else 3
                self.prestige += gain
                msg += f" Presztízs +{gain}."
            if line == "church":
                new_rel = min(2, max(p.religion, tier + 1))
                if new_rel != p.religion:
                    p.religion = new_rel
                    msg += f" A tartomány vallása: {RELIGION[new_rel]}."
        if p.is_player:
            self.add_log(msg)
        # territory is recomputed once at the end of end_turn()
