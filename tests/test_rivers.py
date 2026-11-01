"""F02 — edge rivers. Run: python -m unittest discover tests"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hexcore import hex_corner_keys  # noqa: E402
from world import RIVER_COUNT, World  # noqa: E402

SEEDS = range(50)


class EdgeRiverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds = [World(seed=s) for s in SEEDS]

    def test_count(self):
        for w in self.worlds:
            self.assertLessEqual(len(w.rivers), RIVER_COUNT[1], w.seed)
            terrains = {t.terrain for t in w.tiles.values()}
            if "water" in terrains and terrains & {"hills", "mountain"}:
                self.assertGreaterEqual(len(w.rivers), 1, w.seed)

    def test_paths_are_connected_edges_without_loops(self):
        for w in self.worlds:
            for river in w.rivers:
                self.assertEqual(len(river), len(set(river)), w.seed)
                for c1, c2 in zip(river, river[1:]):
                    edge = c1 & c2
                    self.assertEqual(len(edge), 2, w.seed)
                    self.assertTrue(any(h in w.tiles for h in edge), w.seed)

    def test_source_and_mouth(self):
        for w in self.worlds:
            earlier = set()
            for river in w.rivers:
                def water(c):
                    return any(h in w.tiles and w.tiles[h].terrain == "water" for h in c)
                src = river[0]
                self.assertTrue(any(h in w.tiles and w.tiles[h].terrain in ("hills", "mountain")
                                    for h in src), w.seed)
                self.assertTrue(water(river[-1]) or river[-1] in earlier, w.seed)
                for c in river[:-1]:
                    self.assertFalse(water(c), w.seed)
                    self.assertNotIn(c, earlier, w.seed)
                earlier.update(river)

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
