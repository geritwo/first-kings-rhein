"""F07b — Integration & Settlement meters. Run: python -m unittest discover tests"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world import World, load_meter_rules  # noqa: E402

SEEDS = range(10)
SEASONS_RUN = 40


def levels_reached(thresholds, progress):
    return sum(1 for t in thresholds if progress >= t)


def roman_vassal(w):
    """Test setup: bring a Roman-Gallic province under the crown (F18 will do this in play)."""
    p = next(p for p in w.provinces if p.faction == "roman")
    p.status = "vassal"
    return p


class MeterStartTest(unittest.TestCase):
    def test_ranges_and_start_values(self):
        for s in SEEDS:
            w = World(seed=s)
            for p in w.provinces:
                self.assertTrue(0 <= p.integration <= w.integration_max(), (s, p.name))
                self.assertTrue(0 <= p.settlement <= w.settlement_max(), (s, p.name))
                if p.is_player:
                    self.assertEqual((p.integration, p.settlement), (5, 4), (s, p.name))
                else:
                    self.assertEqual((p.integration, p.settlement), (0, 0), (s, p.name))

    def test_same_seed_same_meters(self):
        a, b = World(seed=3), World(seed=3)
        for _ in range(12):
            a.end_turn()
            b.end_turn()
        snap = lambda w: [(p.name, p.integration, p.settlement,
                           p.integration_progress, p.settlement_progress) for p in w.provinces]
        self.assertEqual(snap(a), snap(b))


class MeterPlayTest(unittest.TestCase):
    def test_never_decrease_and_independents_stay(self):
        for s in SEEDS:
            w = World(seed=s)
            prev = {p.name: (p.integration, p.settlement) for p in w.provinces}
            for _ in range(SEASONS_RUN):
                w.end_turn()
                for p in w.provinces:
                    i, st = prev[p.name]
                    self.assertGreaterEqual(p.integration, i, (s, p.name))
                    self.assertGreaterEqual(p.settlement, st, (s, p.name))
                    prev[p.name] = (p.integration, p.settlement)
                    if not p.is_player:
                        self.assertEqual((p.integration, p.settlement), (0, 0), (s, p.name))
                        self.assertEqual((p.integration_progress, p.settlement_progress),
                                         (0.0, 0.0), (s, p.name))

    def test_integration_rises_with_church_exactly_at_thresholds(self):
        w = World(seed=7)
        p = roman_vassal(w)
        th = w.meter_rules["integration_thresholds"]
        self.assertGreaterEqual(w.best_tier(p, "church"), 0)   # Roman provinces start with one
        for _ in range(SEASONS_RUN):
            w.end_turn()
            self.assertLessEqual(p.integration, 5)
            self.assertEqual(p.integration,
                             min(len(th), levels_reached(th, p.integration_progress)))
        self.assertGreater(p.integration, 0)

    def test_settlement_rises_with_knights_exactly_at_thresholds(self):
        w = World(seed=7)
        p = roman_vassal(w)
        th = w.meter_rules["settlement_thresholds"]
        self.assertGreaterEqual(w.knights(p), 1)
        for _ in range(SEASONS_RUN):
            w.end_turn()
            self.assertLessEqual(p.settlement, 4)
            self.assertEqual(p.settlement,
                             min(len(th), levels_reached(th, p.settlement_progress)))
        self.assertGreater(p.settlement, 0)

    def test_ruler_presence_adds_exactly_the_lever(self):
        w = World(seed=7)
        p = roman_vassal(w)
        apart = w._meter_gains(p)[0]
        w.ruler.hex = p.seat
        self.assertTrue(w.ruler_present(p))
        together = w._meter_gains(p)[0]
        self.assertEqual(together - apart, w.meter_rules["integration_levers"]["ruler_present"])

    def test_level_up_is_logged(self):
        w = World(seed=7)
        p = roman_vassal(w)
        for _ in range(SEASONS_RUN):
            before = p.integration
            w.end_turn()
            if p.integration > before:
                line = next(l for l in reversed(w.log) if "Integráció" in l)
                self.assertIn(p.name, line)
                self.assertIn(f"{p.integration}/5", line)
                return
        self.fail("Integration never rose in 40 seasons")


class TensionTest(unittest.TestCase):
    def test_range_and_extremes(self):
        w = World(seed=7)
        for p in w.provinces:
            self.assertTrue(0.0 <= w.tension(p) <= 1.0, p.name)
            self.assertEqual(w.tension(p), 0.0, p.name)      # 5/4 or 0/0 at the start
        p = w.provinces[0]
        p.integration, p.settlement = 5, 0
        self.assertEqual(w.tension(p), 1.0)
        p.integration, p.settlement = 0, 4
        self.assertEqual(w.tension(p), 1.0)
        p.integration, p.settlement = 5, 4
        self.assertEqual(w.tension(p), 0.0)

    def test_weight(self):
        w = World(seed=7)
        p = w.provinces[0]
        p.integration, p.settlement = 5, 2
        self.assertAlmostEqual(w.tension(p), 0.5)
        self.assertAlmostEqual(w.tension_weight(p),
                               w.meter_rules["tension_base_weight"] * 0.5)


class DataDrivenTest(unittest.TestCase):
    def test_rules_come_from_the_data_dict(self):
        rules = copy.deepcopy(load_meter_rules())
        rules["integration_thresholds"] = [1, 1, 1]
        rules["integration_levers"]["church_per_tier"] = 100
        rules["start"]["others"] = {"integration": 1, "settlement": 2}
        w = World(seed=7, meter_rules=rules)
        self.assertEqual(w.integration_max(), 3)
        p = roman_vassal(w)
        self.assertEqual((p.integration, p.settlement), (1, 2))
        w.end_turn()
        self.assertEqual(p.integration, 3)       # capped at the new maximum

    def test_data_file_is_valid(self):
        r = load_meter_rules()
        for key in ("integration_thresholds", "settlement_thresholds"):
            self.assertEqual(r[key], sorted(r[key]))
        self.assertEqual(len(r["integration_thresholds"]), 5)
        self.assertEqual(len(r["settlement_thresholds"]), 4)


if __name__ == "__main__":
    unittest.main()
