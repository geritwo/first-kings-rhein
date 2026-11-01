"""F02 — edge rivers. Run: python -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hexcore import hex_corner_keys, neighbors  # noqa: E402
from hexcore import axial_to_offset, corner_pixel  # noqa: E402
from world import (COAST_MIN_SHARE, COAST_SIDES, RIVER_CENTRE, RIVER_COUNT,  # noqa: E402
                   RIVER_FLAT, RIVER_MAJOR_COUNT, World)

SEEDS = range(50)


class EdgeRiverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds = [World(seed=s) for s in SEEDS]

    def test_count(self):
        for w in self.worlds:
            self.assertLessEqual(len(w.rivers), RIVER_COUNT[1], w.seed)
            terrains = {t.terrain for t in w.tiles.values()}
            if terrains & {"water", "sea"} and terrains & {"hills", "mountain"}:
                self.assertGreaterEqual(len(w.rivers), 1, w.seed)

    def test_paths_are_connected_edges_without_loops(self):
        for w in self.worlds:
            for river in w.rivers:
                self.assertEqual(len(river), len(set(river)), w.seed)
                for c1, c2 in zip(river, river[1:]):
                    edge = c1 & c2
                    self.assertEqual(len(edge), 2, w.seed)
                    self.assertTrue(all(h in w.tiles for h in edge), w.seed)  # not on the border

    def test_source_and_mouth(self):
        for w in self.worlds:
            earlier = set()
            for river in w.rivers:
                def water(c):
                    return any(h in w.tiles and w.tiles[h].terrain in ("water", "sea")
                               for h in c)
                src = river[0]
                if not any(river is m for m in w.rivers[:w.n_major_rivers]):
                    # majors may fall back to high lowland corners
                    self.assertTrue(any(h in w.tiles and w.tiles[h].terrain
                                        in ("hills", "mountain") for h in src), w.seed)
                self.assertTrue(water(river[-1]) or river[-1] in earlier, w.seed)
                for c in river[:-1]:
                    self.assertFalse(water(c), w.seed)
                    self.assertNotIn(c, earlier, w.seed)
                earlier.update(river)
                for b in w.river_branches:      # its island channels count too
                    if b[0] in river:
                        earlier.update(b)

    def test_coast(self):
        """One of W / NW / N always has sea on >= 30% of its map border."""
        for w in self.worlds:
            self.assertIn(w.coast_side, COAST_SIDES)
            border = [h for h, t in w.tiles.items() if w._coast_border(t.col, t.row)]
            sea = sum(w.tiles[h].terrain == "sea" for h in border)
            self.assertGreaterEqual(sea, COAST_MIN_SHARE * len(border), w.seed)

    def test_major_rivers(self):
        """At least 2 major rivers cross the central plains and reach the sea."""
        lo, hi = RIVER_CENTRE
        for w in self.worlds:
            self.assertGreaterEqual(w.n_major_rivers, RIVER_MAJOR_COUNT, w.seed)
            for river in w.rivers[:w.n_major_rivers]:
                self.assertTrue(any(w.tiles[h].terrain == "sea" for h in river[-1]
                                    if h in w.tiles), w.seed)

                def central_flat(c):
                    offs = [axial_to_offset(*h) for h in c]
                    return (all(h in w.tiles and w.tiles[h].terrain in RIVER_FLAT for h in c)
                            and any(lo * w.width <= col <= hi * w.width
                                    and lo * w.height <= row <= hi * w.height
                                    for col, row in offs))
                self.assertTrue(any(central_flat(c) for c in river), w.seed)

    def test_mountain_ridges(self):
        """Mountains are single-hex ridges: no mountain hex sits in a 2-wide
        band it could be peeled from (neighbours forming one arc of 2-5)."""
        for w in self.worlds:
            mtn = {h for h, t in w.tiles.items() if t.terrain == "mountain"}
            for h in mtn:
                ring = [n in mtn for n in neighbors(h)]
                arcs = sum(1 for i in range(6) if ring[i] and not ring[i - 1])
                self.assertFalse(arcs == 1 and 2 <= sum(ring) <= 5, (w.seed, h))

    def test_flat_rivers_meander(self):
        """On flat land, 24-edge stretches are clearly longer than the straight
        line (a straight hex-edge zigzag is ~1.2-1.3)."""
        ratios = []
        for w in self.worlds:
            for r in w.rivers:
                for i in range(0, len(r) - 24, 6):
                    win = r[i:i + 25]
                    if all(w.tiles[h].terrain in RIVER_FLAT
                           for c in win for h in c if h in w.tiles):
                        (ax, ay), (bx, by) = corner_pixel(win[0], 1), corner_pixel(win[-1], 1)
                        ratios.append(24 / max(0.5, ((ax - bx) ** 2 + (ay - by) ** 2) ** .5))
        ratios.sort()
        self.assertGreaterEqual(ratios[len(ratios) // 2], 1.6)

    def test_islands(self):
        """A branch leaves and rejoins its river round one hex: an island."""
        self.assertTrue(any(w.river_branches for w in self.worlds))
        for w in self.worlds:
            for branch in w.river_branches:
                parent = next(r for r in w.rivers if branch[0] in r and branch[-1] in r)
                self.assertLess(parent.index(branch[0]), parent.index(branch[-1]), w.seed)
                island = set.intersection(*(set(c) for c in branch))
                self.assertEqual(len(island), 1, w.seed)
                h = island.pop()
                for n in neighbors(h):
                    self.assertTrue(w.is_river_edge(h, n), (w.seed, h))
                for c1, c2 in zip(branch, branch[1:]):
                    self.assertEqual(len(c1 & c2), 2, w.seed)

    def test_tile_flag_matches_edges(self):
        for w in self.worlds:
            bordering = {h for e in w.river_edges for h in e if h in w.tiles}
            flagged = {h for h, t in w.tiles.items() if t.river}
            self.assertEqual(bordering, flagged, w.seed)
            for e in w.river_edges:
                a, b = tuple(e)
                self.assertTrue(w.is_river_edge(a, b))

    def test_corners_of_hex_are_its_own(self):
        h = (3, 4)
        corners = hex_corner_keys(h)
        self.assertEqual(len(set(corners)), 6)
        for c in corners:
            self.assertIn(h, c)
            self.assertEqual(len(c), 3)

    def test_deterministic(self):
        a, b = World(seed=7), World(seed=7)
        self.assertEqual(a.rivers, b.rivers)


if __name__ == "__main__":
    unittest.main()
