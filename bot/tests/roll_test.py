import os
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import ChatMemberAdministrator, User

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

# Importing a skill executes skills/__init__.py, whose optional integrations
# read these environment variables during module initialization.
from skills.roll import (  # noqa: E402  # pylint: disable=wrong-import-position
    ADMIN_RIGHT_FIELDS,
    _demote_admin_for_roll,  # pyright: ignore[reportPrivateUsage]
    _restore_admin,  # pyright: ignore[reportPrivateUsage]
    get_mute_minutes,
)


def make_admin(*, can_be_edited: bool = True) -> ChatMemberAdministrator:
    return ChatMemberAdministrator(
        user=User(id=42, first_name="Test", is_bot=False),
        can_be_edited=can_be_edited,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=False,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
        can_pin_messages=True,
        can_manage_topics=False,
        custom_title="aoc winner",
    )


class RollAdminTest(IsolatedAsyncioTestCase):
    def test_production_mute_progression(self):
        mute_hours = [get_mute_minutes(n) // 60 for n in range(5, -1, -1)]
        self.assertEqual(mute_hours, [16, 32, 48, 64, 80, 96])

    async def test_demotes_editable_admin_and_saves_exact_rights(self):
        member = make_admin()
        bot = AsyncMock()
        bot.get_chat_member.return_value = member
        job_queue = MagicMock()
        context = cast(Any, SimpleNamespace(bot=bot, job_queue=job_queue))
        update = cast(Any, SimpleNamespace(effective_chat=SimpleNamespace(id=-100123)))

        with patch("skills.roll.db") as database:
            result = await _demote_admin_for_roll(
                update, context, member.user, timedelta(hours=16)
            )

        self.assertTrue(result)
        saved = database.save_roll_admin_restoration.call_args.kwargs
        self.assertEqual(saved["custom_title"], "aoc winner")
        self.assertTrue(saved["rights"]["can_manage_chat"])
        self.assertTrue(saved["rights"]["can_invite_users"])
        self.assertTrue(saved["rights"]["can_pin_messages"])

        demotion = bot.promote_chat_member.await_args.kwargs
        self.assertEqual(set(demotion), set(ADMIN_RIGHT_FIELDS))
        self.assertFalse(any(demotion.values()))
        job_queue.run_once.assert_called_once()

    async def test_does_not_demote_uneditable_admin(self):
        member = make_admin(can_be_edited=False)
        bot = AsyncMock()
        bot.get_chat_member.return_value = member
        context = cast(Any, SimpleNamespace(bot=bot, job_queue=MagicMock()))
        update = cast(Any, SimpleNamespace(effective_chat=SimpleNamespace(id=-1)))

        with patch("skills.roll.db") as database:
            result = await _demote_admin_for_roll(
                update, context, member.user, timedelta(hours=16)
            )

        self.assertFalse(result)
        database.save_roll_admin_restoration.assert_not_called()
        bot.promote_chat_member.assert_not_awaited()

    async def test_restores_rights_and_custom_title(self):
        bot = AsyncMock()
        context = cast(Any, SimpleNamespace(bot=bot))
        restoration = {
            "chat_id": -100123,
            "user_id": 42,
            "rights": {
                field: field == "can_manage_chat" for field in ADMIN_RIGHT_FIELDS
            },
            "custom_title": "aoc winner",
        }

        with patch("skills.roll.db") as database:
            result = await _restore_admin(context, restoration)

        self.assertTrue(result)
        bot.promote_chat_member.assert_awaited_once()
        bot.set_chat_administrator_custom_title.assert_awaited_once_with(
            -100123, 42, "aoc winner"
        )
        database.delete_roll_admin_restoration.assert_called_once_with(-100123, 42)
