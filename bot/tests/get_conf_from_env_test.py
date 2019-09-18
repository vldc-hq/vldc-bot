import os
from typing import Dict
from unittest import TestCase

from config import get_config


class ConfigTestCase(TestCase):
    def setUp(self) -> None:
        self.env_debug = "True"
        self.env_chat_id = "@vldc_best_chat"
        self.env_token = "my-secret-token"
        self.env_mongo_initdb_root_username = "root"
        self.env_mongo_initdb_root_password = "my-mega-secret-password"

        os.environ["DEBUG"] = self.env_debug
        os.environ["CHAT_ID"] = self.env_chat_id
        os.environ["TOKEN"] = self.env_token
        os.environ["MONGO_INITDB_ROOT_USERNAME"] = self.env_mongo_initdb_root_username
        os.environ["MONGO_INITDB_ROOT_PASSWORD"] = self.env_mongo_initdb_root_password

    def test_get_config(self):
        c: Dict = get_config()
        self.assertEqual(c["DEBUG"], self.env_debug)
        self.assertEqual(c["GROUP_CHAT_ID"], self.env_chat_id)
        self.assertEqual(c["TOKEN"], self.env_token)
        self.assertEqual(c["MONGO_USER"], self.env_mongo_initdb_root_username)
        self.assertEqual(c["MONGO_PASS"], self.env_mongo_initdb_root_password)
