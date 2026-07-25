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
    catch_reply,
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


class TowelReplyTest(IsolatedAsyncioTestCase):
    async def test_short_ephemeral_reply_gets_private_feedback(self):
        user = User(id=USER_ID, first_name="Human", is_bot=False)
        message = SimpleNamespace(
            message_id=0,
            text="short",
            api_kwargs={"ephemeral_message_id": 17},
            reply_to_message=None,
        )
        update = cast(
            Any,
            SimpleNamespace(
                message=message,
                effective_message=message,
                effective_user=user,
                effective_chat=SimpleNamespace(id=CHAT_ID),
            ),
        )
        bot = AsyncMock()
        context = cast(Any, SimpleNamespace(bot=bot))

        with patch("skills.towel_mode.sqlite_db") as database:
            database.find_quarantine_user.return_value = {
                "_id": USER_ID,
                "rel_messages": [],
            }
            await catch_reply(update, context)

        bot.delete_message.assert_not_awaited()
        send_call = bot.send_message.await_args
        self.assertEqual(send_call.args[0], CHAT_ID)
        self.assertIn("слишком короткий", send_call.args[1])
        self.assertEqual(send_call.kwargs["api_kwargs"], {"receiver_user_id": USER_ID})
        database.add_quarantine_rel_message.assert_not_called()

    async def test_valid_ephemeral_reply_gets_public_welcome(self):
        user = User(id=USER_ID, first_name="Human", is_bot=False)
        message = SimpleNamespace(
            message_id=0,
            text="I love VLDC and write Rust",
            api_kwargs={"ephemeral_message_id": 18},
            reply_to_message=None,
        )
        update = cast(
            Any,
            SimpleNamespace(
                message=message,
                effective_message=message,
                effective_user=user,
                effective_chat=SimpleNamespace(id=CHAT_ID),
            ),
        )
        bot = AsyncMock()
        context = cast(Any, SimpleNamespace(bot=bot))

        with patch("skills.towel_mode.sqlite_db") as database:
            database.find_quarantine_user.return_value = {
                "_id": USER_ID,
                "rel_messages": [],
            }
            await catch_reply(update, context)

        bot.delete_message.assert_not_awaited()
        database.delete_quarantine_user.assert_called_once_with(user_id=USER_ID)
        bot.send_message.assert_awaited_once_with(CHAT_ID, "Добро пожаловать в VLDC!")

    async def test_public_message_from_quarantined_user_is_deleted(self):
        user = User(id=USER_ID, first_name="Human", is_bot=False)
        message = SimpleNamespace(
            message_id=23,
            text="public text",
            api_kwargs={},
            reply_to_message=None,
        )
        update = cast(
            Any,
            SimpleNamespace(
                message=message,
                effective_message=message,
                effective_user=user,
                effective_chat=SimpleNamespace(id=CHAT_ID),
            ),
        )
        bot = AsyncMock()
        context = cast(Any, SimpleNamespace(bot=bot))

        with patch("skills.towel_mode.sqlite_db") as database:
            database.find_quarantine_user.return_value = {
                "_id": USER_ID,
                "rel_messages": [],
            }
            await catch_reply(update, context)

        bot.delete_message.assert_awaited_once_with(
            chat_id=CHAT_ID,
            message_id=23,
        )
        bot.send_message.assert_not_awaited()
