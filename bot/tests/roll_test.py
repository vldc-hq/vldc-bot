import os
from types import SimpleNamespace
from typing import Any, cast
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from telegram import User

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from skills.roll import (  # noqa: E402  # pylint: disable=wrong-import-position
    FALSE_STARTS_KEY,
    LAST_ROLLER_KEY,
    REPEAT_ROLL_MUTE,
    _handle_false_start,  # pyright: ignore[reportPrivateUsage]
    _register_roll_attempt,  # pyright: ignore[reportPrivateUsage]
    roll,
)


class RollTurnTest(TestCase):
    def test_users_must_take_turns(self):
        context = cast(Any, SimpleNamespace(chat_data={}))

        self.assertEqual(_register_roll_attempt(context, 1), 0)
        self.assertEqual(_register_roll_attempt(context, 1), 1)
        self.assertEqual(_register_roll_attempt(context, 1), 2)
        self.assertEqual(_register_roll_attempt(context, 2), 0)
        self.assertEqual(_register_roll_attempt(context, 1), 0)
        self.assertEqual(_register_roll_attempt(context, 1), 1)

    def test_turns_are_tracked_per_chat(self):
        first_chat = cast(Any, SimpleNamespace(chat_data={}))
        second_chat = cast(Any, SimpleNamespace(chat_data={}))

        self.assertEqual(_register_roll_attempt(first_chat, 1), 0)
        self.assertEqual(_register_roll_attempt(first_chat, 1), 1)
        self.assertEqual(_register_roll_attempt(second_chat, 1), 0)


class RepeatRollTest(IsolatedAsyncioTestCase):
    async def test_first_false_start_warns_and_second_one_mutes(self):
        user = User(id=1, first_name="Impatient", is_bot=False)
        message = SimpleNamespace(message_id=10)
        update = cast(
            Any,
            SimpleNamespace(
                message=message,
                effective_chat=SimpleNamespace(id=-100),
            ),
        )
        bot = AsyncMock()
        context = cast(Any, SimpleNamespace(bot=bot, job_queue=None))

        with (
            patch("skills.roll.mute_user_for_time", new=AsyncMock()) as mute,
            patch("skills.roll.cleanup_queue_update") as cleanup,
        ):
            await _handle_false_start(update, context, user, 1)
            mute.assert_not_awaited()
            self.assertIn("Это предупреждение", bot.send_message.await_args.args[1])

            await _handle_false_start(update, context, user, 2)

        mute.assert_awaited_once_with(update, context, user, REPEAT_ROLL_MUTE)
        self.assertEqual(REPEAT_ROLL_MUTE.total_seconds(), 5 * 60)
        self.assertIn("без зачёта в клуб", bot.send_message.await_args.args[1])
        self.assertEqual(cleanup.call_count, 2)
        for cleanup_call in cleanup.call_args_list:
            self.assertEqual(cleanup_call.args[0], context.job_queue)
            self.assertIs(cleanup_call.args[1], message)
            self.assertEqual(cleanup_call.args[3], 120)
            self.assertEqual(
                cleanup_call.kwargs,
                {"remove_cmd": True, "remove_reply": False},
            )

    async def test_repeat_roll_does_not_touch_barrel_or_hussar_stats(self):
        user = User(id=1, first_name="Impatient", is_bot=False)
        message = SimpleNamespace(message_id=10)
        update = cast(
            Any,
            SimpleNamespace(
                message=message,
                effective_chat=SimpleNamespace(id=-100),
                effective_user=user,
            ),
        )
        context = cast(
            Any,
            SimpleNamespace(
                chat_data={LAST_ROLLER_KEY: user.id, FALSE_STARTS_KEY: 0},
                bot=AsyncMock(),
            ),
        )

        with (
            patch("skills.roll._handle_false_start", new=AsyncMock()) as handle,
            patch("skills.roll._shot") as shot,
            patch("skills.roll.db") as database,
        ):
            await roll(update, context)

        handle.assert_awaited_once_with(update, context, user, 1)
        shot.assert_not_called()
        database.find_hussar.assert_not_called()
