import unittest
from datetime import datetime, timezone, timedelta
from dst_schedule_extractor.core import get_dst_transitions


class TestGetDstTransitions(unittest.TestCase):

    def test_us_eastern_2024_spring_and_fall(self):
        spring, fall = get_dst_transitions("America/New_York", 2024)
        self.assertIsNotNone(spring)
        self.assertIsNotNone(fall)
        # In 2024 US DST: spring forward Mar 10 02:00 -> 03:00 EST->EDT
        # UTC offset goes from -05:00 to -04:00. The returned datetime is
        # in the zone's own frame, so after spring the offset is -04:00.
        self.assertEqual(spring.utcoffset(), timedelta(hours=-4))
        self.assertEqual(spring.month, 3)
        self.assertEqual(spring.day, 10)
        self.assertEqual(fall.month, 11)
        self.assertEqual(fall.day, 3)
        # Fall back: offset returns to -05:00
        self.assertEqual(fall.utcoffset(), timedelta(hours=-5))

    def test_utc_no_dst(self):
        spring, fall = get_dst_transitions("UTC", 2024)
        self.assertIsNone(spring)
        self.assertIsNone(fall)

    def test_fixed_offset_zone_no_dst(self):
        # Etc/GMT+5 is a fixed offset with no DST (note IANA sign convention).
        spring, fall = get_dst_transitions("Etc/GMT+5", 2024)
        self.assertIsNone(spring)
        self.assertIsNone(fall)

    def test_arizona_no_dst(self):
        # Most of Arizona does not observe DST.
        spring, fall = get_dst_transitions("America/Phoenix", 2024)
        self.assertIsNone(spring)
        self.assertIsNone(fall)

    def test_southern_hemisphere_australia_2023(self):
        # Australia/Sydney springs forward in October and falls back in April.
        spring, fall = get_dst_transitions("Australia/Sydney", 2023)
        self.assertIsNotNone(spring)
        self.assertIsNotNone(fall)
        self.assertEqual(fall.month, 4)  # first Sunday April 2023
        self.assertEqual(fall.day, 2)
        self.assertEqual(spring.month, 10)
        self.assertEqual(spring.day, 1)

    def test_europe_london_2024(self):
        spring, fall = get_dst_transitions("Europe/London", 2024)
        self.assertIsNotNone(spring)
        self.assertIsNotNone(fall)
        # EU rules: last Sunday March and last Sunday October.
        self.assertEqual(spring.month, 3)
        self.assertEqual(spring.day, 31)
        self.assertEqual(fall.month, 10)
        self.assertEqual(fall.day, 27)
        # After spring, BST = UTC+1
        self.assertEqual(spring.utcoffset(), timedelta(hours=1))
        # After fall, GMT = UTC+0
        self.assertEqual(fall.utcoffset(), timedelta(hours=0))

    def test_aware_datetimes_returned(self):
        spring, fall = get_dst_transitions("America/New_York", 2024)
        for dt in (spring, fall):
            self.assertIsNotNone(dt)
            self.assertIsNotNone(dt.tzinfo)
            # Naive datetimes have tzinfo is None; ensure not naive.
            self.assertNotEqual(dt.tzinfo, None)

    def test_ordering_spring_before_fall(self):
        spring, fall = get_dst_transitions("America/New_York", 2024)
        self.assertIsNotNone(spring)
        self.assertIsNotNone(fall)
        self.assertLess(spring, fall)

    def test_year_without_dst_returns_none_pair(self):
        # Pick a year far in the future where tzdata still shows no DST for
        # a non-DST zone. Use a stable perennial zone.
        spring, fall = get_dst_transitions("America/Phoenix", 2030)
        self.assertIsNone(spring)
        self.assertIsNone(fall)

    def test_invalid_zone_raises(self):
        with self.assertRaises(Exception):
            get_dst_transitions("Nonexistent/Zone", 2024)

    def test_returns_tuple_of_two(self):
        result = get_dst_transitions("UTC", 2024)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
