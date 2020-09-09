from datetime import timedelta
from unittest import TestCase

from utils.time import get_duration


class DurationParserTestCase(TestCase):
    def test_get_secs(self):
        self.assertEqual(get_duration('20s'), timedelta(seconds=20))
        self.assertEqual(get_duration('20s  '), timedelta(seconds=20))
        self.assertEqual(get_duration('     20s  '), timedelta(seconds=20))

    def test_get_mins(self):
        self.assertEqual(get_duration('20m'), timedelta(minutes=20))
        self.assertEqual(get_duration('20m  '), timedelta(minutes=20))
        self.assertEqual(get_duration('     20m  '), timedelta(minutes=20))

    def test_get_hours(self):
        self.assertEqual(get_duration('20h'), timedelta(hours=20))
        self.assertEqual(get_duration('20h  '), timedelta(hours=20))
        self.assertEqual(get_duration('     20h  '), timedelta(hours=20))

    def test_get_mix(self):
        self.assertEqual(get_duration('2h 30m 10s'), timedelta(hours=2, minutes=30, seconds=10))
        self.assertEqual(get_duration('2h   30m 10s'), timedelta(hours=2, minutes=30, seconds=10))
        self.assertEqual(get_duration('     2h   30m 10s'), timedelta(hours=2, minutes=30, seconds=10))

    def test_get_default(self):
        self.assertEqual(get_duration('600'), timedelta(minutes=600))
        self.assertEqual(get_duration('600  '), timedelta(minutes=600))
        self.assertEqual(get_duration('     600  '), timedelta(minutes=600))

    def test_get_bad_raw_duration(self):
        self.assertEqual(get_duration('php sucks!'), timedelta(0))
        self.assertEqual(get_duration('php 20s sucks!'), timedelta(seconds=20))
        self.assertEqual(get_duration('php 20s sucks 40m !'), timedelta(seconds=20, minutes=40))

    def test_get_duration_lt_10(self):
        self.assertEqual(get_duration('9'), timedelta(minutes=9))
        self.assertEqual(get_duration('900'), timedelta(minutes=900))
        self.assertEqual(get_duration('1'), timedelta(minutes=1))
