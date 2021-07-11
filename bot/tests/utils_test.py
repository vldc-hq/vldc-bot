from datetime import timedelta
from unittest import TestCase

from bot.utils.time import get_duration


class DurationParserTestCase(TestCase):
    def test_get_secs(self):
        self.assertEqual(get_duration('20s'), timedelta(seconds=20))

    def test_get_mins(self):
        self.assertEqual(get_duration('20m'), timedelta(minutes=20))

    def test_get_hours(self):
        self.assertEqual(get_duration('20h'), timedelta(hours=20))

    def test_get_days(self):
        self.assertEqual(get_duration('3d'), timedelta(days=3))

    def test_get_week(self):
        self.assertEqual(get_duration('28w'), timedelta(weeks=28))

    def test_get_mix(self):
        self.assertEqual(get_duration('2h 30m 10s'), timedelta(hours=2, minutes=30, seconds=10))
        self.assertEqual(get_duration('2d 4h 45m 5s'), timedelta(
            days=2,
            hours=4,
            minutes=45,
            seconds=5,
        ))
        self.assertEqual(get_duration('1w 2d 3h 4m 5s'), timedelta(
            days=9,
            hours=3,
            minutes=4,
            seconds=5,
        ))
        self.assertEqual(get_duration('2w 4d'), timedelta(weeks=2, days=4))

    def test_wrong_order(self):
        self.assertEqual(get_duration('4m 3w'), timedelta(weeks=3, minutes=4))

    def test_get_default(self):
        self.assertEqual(get_duration('600'), timedelta(minutes=600))

    def test_get_bad_raw_duration(self):
        self.assertEqual(get_duration('php sucks!'), timedelta(0))
        self.assertEqual(get_duration('php 20s sucks!'), timedelta(seconds=20))
        self.assertEqual(get_duration('php 20s sucks 40m !'), timedelta(seconds=20, minutes=40))

    def test_get_duration_lt_10(self):
        self.assertEqual(get_duration('9'), timedelta(minutes=9))
        self.assertEqual(get_duration('900'), timedelta(minutes=900))
        self.assertEqual(get_duration('1'), timedelta(minutes=1))

    def test_get_duration_with_dots(self):
        self.assertEqual(get_duration('666.666'), timedelta(minutes=0))

    def test_trailing_whitespace(self):
        self.assertEqual(get_duration('20s  '), timedelta(seconds=20))
        self.assertEqual(get_duration('     20s  '), timedelta(seconds=20))

        self.assertEqual(get_duration('20m  '), timedelta(minutes=20))
        self.assertEqual(get_duration('     20m  '), timedelta(minutes=20))

        self.assertEqual(get_duration('20h  '), timedelta(hours=20))
        self.assertEqual(get_duration('     20h  '), timedelta(hours=20))

        self.assertEqual(get_duration('2h   30m 10s'), timedelta(hours=2, minutes=30, seconds=10))
        self.assertEqual(get_duration('     2h   30m 10s'), timedelta(hours=2, minutes=30, seconds=10))

        self.assertEqual(get_duration('600  '), timedelta(minutes=600))
        self.assertEqual(get_duration('     600  '), timedelta(minutes=600))
