import os
from types import SimpleNamespace
from typing import Any, cast
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from telegram import User

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from skills.towel_mode import (  # noqa: E402  # pylint: disable=wrong-import-position
    QUARANTINE_TIME,
    quarantine_user,
)

CHAT_ID = -100123
USER_ID = 42


class TowelChallengeTest(IsolatedAsyncioTestCase):
    async def test_human_gets_ephemeral_challenge(self):
        user = User(id=USER_ID, first_name="Human", is_bot=False)
        bot = AsyncMock()
        bot.send_message.return_value = SimpleNamespace(message_id=0)
        context = cast(Any, SimpleNamespace(bot=bot))

        with patch("skills.towel_mode.sqlite_db") as database:
            await quarantine_user(user, CHAT_ID, context)

        database.add_quarantine_user.assert_called_once_with(USER_ID, QUARANTINE_TIME)
        send_call = bot.send_message.await_args
        self.assertEqual(send_call.args[0], CHAT_ID)
        self.assertEqual(send_call.kwargs["api_kwargs"], {"receiver_user_id": USER_ID})
        database.add_quarantine_rel_message.assert_not_called()
        bot.get_me.assert_not_awaited()

    async def test_bot_keeps_public_challenge(self):
        user = User(id=USER_ID, first_name="Other bot", is_bot=True)
        bot = AsyncMock()
        bot.send_message.return_value = SimpleNamespace(message_id=77)
        bot.get_me.return_value = User(id=99, first_name="VLDC bot", is_bot=True)
        context = cast(Any, SimpleNamespace(bot=bot))

        with patch("skills.towel_mode.sqlite_db") as database:
            await quarantine_user(user, CHAT_ID, context)

        send_call = bot.send_message.await_args
        self.assertNotIn("api_kwargs", send_call.kwargs)
        database.add_quarantine_rel_message.assert_called_once_with(USER_ID, 77)
