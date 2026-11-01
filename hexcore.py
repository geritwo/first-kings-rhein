"""
Hex core — the math and pathfinding from hex_engine_turns.py, generalised.

Changes compared to the MVP engine:
  * move costs are weighted (terrain, roads) instead of a uniform +1
  * pathfinding and the Dijkstra flood-fill take a `cost(a, b)` callback,
    so the same functions serve unit movement AND territory control
  * a multi-source flood-fill assigns hexes to the nearest province

Axial coordinates, pointy-top orientation, as before.
"""

import heapq
import math

SQRT3 = math.sqrt(3)

# Axial directions, pointy-top.  Order matters: EDGE_CORNERS below is aligned.
DIRECTIONS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]

# For each direction: indices of the two hex corners that form the shared edge
# (corners as produced by hex_corners: angle 60*i - 30, pygame y-down).
EDGE_CORNERS = [(0, 1), (5, 0), (4, 5), (3, 4), (2, 3), (1, 2)]


# ----------------------------------------------------------------------
# Hex math
# ----------------------------------------------------------------------
def axial_to_pixel(q, r, size):
    return size * (SQRT3 * q + SQRT3 / 2 * r), size * (1.5 * r)


def pixel_to_axial(x, y, size):
    q = (SQRT3 / 3 * x - 1 / 3 * y) / size
    r = (2 / 3 * y) / size
    return axial_round(q, r)


def axial_round(q, r):
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return int(rq), int(rr)


def hex_distance(a, b):
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(ar - br) + abs(aq + ar - bq - br)) // 2


def hex_corners(cx, cy, size):
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
    return pts


def neighbors(h):
    q, r = h
    for dq, dr in DIRECTIONS:
        yield (q + dq, r + dr)


def offset_to_axial(col, row):
    """'odd-r' offset (rectangular map layout) -> axial."""
    return col - (row - (row & 1)) // 2, row


def axial_to_offset(q, r):
    return q + (r - (r & 1)) // 2, r


# ----------------------------------------------------------------------
# Pathfinding
# ----------------------------------------------------------------------
def find_path(start, goal, cost, min_step=1):
    """A* with weighted steps.

    cost(a, b) -> step cost from a to neighbour b, or None if impassable.
    min_step is the cheapest possible step (keeps the heuristic admissible).
    Returns (path, total_cost) or (None, inf).
    """
    if start == goal:
        return [start], 0
    open_heap = [(0, 0, start)]
    came_from = {start: None}
    g_cost = {start: 0}
    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if current == goal:
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            return path[::-1], g
        if g > g_cost[current]:
            continue
        for n in neighbors(current):
            c = cost(current, n)
            if c is None:
                continue
            ng = g + c
            if ng < g_cost.get(n, math.inf):
                g_cost[n] = ng
                came_from[n] = current
                heapq.heappush(open_heap,
                               (ng + hex_distance(n, goal) * min_step, ng, n))
    return None, math.inf


def flood_fill(sources, cost, budget):
    """Dijkstra flood-fill from one or more sources.

    sources: dict hex -> (start_cost, label)  (label is carried along,
             so this doubles as a multi-source territory assignment)
    Returns dict hex -> (cost, label) for every hex reached within budget.
    """
    best = {}
    heap = []
    for h, (c, label) in sources.items():
        best[h] = (c, label)
        heapq.heappush(heap, (c, id(label) if label is not None else 0, h))
    while heap:
        c, _, current = heapq.heappop(heap)
        if c > best[current][0]:
            continue
        label = best[current][1]
        for n in neighbors(current):
            step = cost(current, n)
            if step is None:
                continue
            nc = c + step
            if nc <= budget and nc < best.get(n, (math.inf, None))[0]:
                best[n] = (nc, label)
                heapq.heappush(heap, (nc, id(label) if label is not None else 0, n))
    return best
