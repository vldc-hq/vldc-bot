import os
import unittest
from datetime import datetime
from typing import Any, Dict, List, Optional
from db.sqlite import BotDB


class TestBotDB(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_bot.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = BotDB(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_trusted_users(self):
        user_id = 123
        admin_id = 456
        self.db.trust_user(user_id, admin_id)
        self.assertTrue(self.db.is_user_trusted(user_id))

        user: Optional[Dict[str, Any]] = self.db.get_trusted_user(user_id)
        self.assertIsNotNone(user)
        if user:
            self.assertEqual(user["user_id"], user_id)
            self.assertEqual(user["by"], admin_id)

        self.db.untrust_user(user_id)
        self.assertFalse(self.db.is_user_trusted(user_id))

    def test_buktopuha(self):
        user_id = 1
        user_meta = {"id": 1, "first_name": "Test"}
        self.db.add_buktopuha_player(user_id, user_meta, score=10)

        player: Optional[Dict[str, Any]] = self.db.find_buktopuha_player(user_id)
        self.assertIsNotNone(player)
        if player:
            self.assertEqual(player["_id"], user_id)
            self.assertEqual(player["total_score"], 10)
            self.assertEqual(player["win_counter"], 1)
            self.assertEqual(player["game_counter"], 0)

        self.db.inc_buktopuha_game_counter(user_id)
        player = self.db.find_buktopuha_player(user_id)
        self.assertIsNotNone(player)
        if player:
            self.assertEqual(player["game_counter"], 1)

        self.db.inc_buktopuha_win(user_id, score=5)
        player = self.db.find_buktopuha_player(user_id)
        self.assertIsNotNone(player)
        if player:
            self.assertEqual(player["win_counter"], 2)
            self.assertEqual(player["total_score"], 15)

        players: List[Dict[str, Any]] = self.db.get_all_buktopuha_players()
        self.assertEqual(len(players), 1)

        self.db.remove_buktopuha_player(user_id)
        self.assertIsNone(self.db.find_buktopuha_player(user_id))

    def test_towel_quarantine(self):
        user_id = 789
        self.db.add_quarantine_user(user_id, quarantine_time_min=60)

        user: Optional[Dict[str, Any]] = self.db.find_quarantine_user(user_id)
        self.assertIsNotNone(user)
        if user:
            self.assertEqual(user["_id"], user_id)
            self.assertEqual(user["rel_messages"], [])

        self.db.add_quarantine_rel_message(user_id, 1001)
        user = self.db.find_quarantine_user(user_id)
        self.assertIsNotNone(user)
        if user:
            self.assertIn(1001, user["rel_messages"])

        users: List[Dict[str, Any]] = self.db.find_all_quarantine_users()
        self.assertEqual(len(users), 1)

        self.db.delete_quarantine_user(user_id)
        self.assertIsNone(self.db.find_quarantine_user(user_id))

    def test_since_topics(self):
        topic = "Rust"
        now = datetime.now()
        self.db.update_since_topic(topic, now, 1)

        t: Dict[str, Any] = self.db.get_since_topic(topic)
        self.assertEqual(t["topic"], topic.lower())
        self.assertEqual(t["count"], 1)

        self.db.update_since_topic(topic, now, 1)
        t = self.db.get_since_topic(topic)
        self.assertEqual(t["count"], 2)

        topics: List[Dict[str, Any]] = self.db.get_all_since_topics(limit=10)
        self.assertEqual(len(topics), 1)

    def test_roll_hussars(self):
        user_id = 2
        user_meta = {"id": 2, "username": "hussar"}
        self.db.add_hussar(user_id, user_meta)

        h: Optional[Dict[str, Any]] = self.db.find_hussar(user_id)
        self.assertIsNotNone(h)
        if h:
            self.assertEqual(h["_id"], user_id)
            self.assertEqual(h["shot_counter"], 0)

        self.db.hussar_miss(user_id)
        h = self.db.find_hussar(user_id)
        self.assertIsNotNone(h)
        if h:
            self.assertEqual(h["shot_counter"], 1)
            self.assertEqual(h["miss_counter"], 1)

        self.db.hussar_dead(user_id, mute_min=60)
        h = self.db.find_hussar(user_id)
        self.assertIsNotNone(h)
        if h:
            self.assertEqual(h["dead_counter"], 1)
            self.assertEqual(h["total_time_in_club"], 3600)

        hussars: List[Dict[str, Any]] = self.db.get_all_hussars()
        self.assertEqual(len(hussars), 1)

    def test_prism_words(self):
        word = "hello"
        self.db.add_prism_word(word)
        self.db.add_prism_word(word)

        words: List[Dict[str, Any]] = self.db.get_all_prism_words()
        self.assertEqual(len(words), 1)
        self.assertEqual(words[0]["word"], word)
        self.assertEqual(words[0]["count"], 2)

    def test_peninsula_users(self):
        user_id = 3
        user_meta = {"id": 3, "name": "Peninsula"}
        self.db.add_peninsula_user(user_id, user_meta)

        users: List[Dict[str, Any]] = self.db.get_best_peninsulas(n=10)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["_id"], user_id)
        self.assertEqual(users[0]["meta"], user_meta)

    def test_aoc_data(self):
        data = {"members": {"1": {"name": "AOC User"}}}
        self.db.update_aoc_data(data)

        stored: Optional[Dict[str, Any]] = self.db.get_aoc_data()
        self.assertEqual(stored, data)

        self.db.remove_all_aoc_data()
        self.assertIsNone(self.db.get_aoc_data())


if __name__ == "__main__":
    unittest.main()
