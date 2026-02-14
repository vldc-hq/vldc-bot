import os
from unittest import TestCase

from config import get_config, Config


class ConfigTestCase(TestCase):
    def setUp(self) -> None:
        self.env_debug = "True"
        self.debugger = ""
        self.env_chat_id = "@vldc_best_chat"
        self.env_token = "my-secret-token"

        os.environ["DEBUG"] = self.env_debug
        os.environ["DEBUGGER"] = self.debugger
        os.environ["CHAT_ID"] = self.env_chat_id
        os.environ["TOKEN"] = self.env_token

    def test_get_config(self):
        c: Config = get_config()
        self.assertEqual(c["DEBUG"], True)
        self.assertEqual(c["GROUP_CHAT_ID"], self.env_chat_id)
        self.assertEqual(c["TOKEN"], self.env_token)
