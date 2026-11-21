import unittest

from voc.counting import count_units, nps, theme_share


class CountingTests(unittest.TestCase):
    def test_units_are_separate_and_unknown_not_merged(self):
        rows = [
            {"case_key": "A", "customer_key": "C1"},
            {"case_key": "A", "customer_key": "C1"},   # cùng case, cùng khách
            {"case_key": "B", "customer_key": "C1"},   # một khách, nhiều case
            {"case_key": "", "customer_key": ""},      # unknown, không gộp
        ]
        r = count_units(rows)
        self.assertEqual(r["items"], 4)
        self.assertEqual(r["cases"], 2)
        self.assertEqual(r["known_customers"], 1)
        self.assertEqual(r["unknown_case_items"], 1)

    def test_theme_share_can_exceed_100_when_summed(self):
        labels = [{"giao_hang", "bao_gia"}, {"giao_hang"}, set()]
        self.assertEqual(theme_share(labels, "giao_hang", 3), 66.7)
        self.assertEqual(theme_share(labels, "bao_gia", 3), 33.3)
        self.assertIsNone(theme_share(labels, "x", 0))

    def test_nps_formula_keeps_7_8_in_denominator(self):
        # 9,10 -> 2 promoters; 5 -> 1 detractor; 7,8 passive; n=5
        self.assertEqual(nps(["9", "10", "5", "7", "8"]), 20.0)

    def test_nps_unavailable_without_ratings(self):
        self.assertIsNone(nps(["", None, "abc", "11"]))


if __name__ == "__main__":
    unittest.main()
