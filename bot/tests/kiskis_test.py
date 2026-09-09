# pylint: disable=wrong-import-position
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from telegram import User, Chat, Message
from telegram.error import BadRequest, TimedOut

os.environ.setdefault("TOKEN", "test-token")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

from db.sqlite import BotDB  # noqa: E402
from db.kiskis import KiskisStore, DAY  # noqa: E402
from skills.kiskis import (  # noqa: E402  # pylint: disable=wrong-import-position
    kiskis,
    feed,
    expire_food,
    restrict,
    add_kiskis,
    WEIGHTS,
)

NOW = 1000000.0
ALICE = User(1, "Alice", False)
BOB = User(2, "Bob", False)


@pytest.fixture(name="store")
def game_store(tmp_path: Path) -> KiskisStore:
    path = str(tmp_path / "game.db")
    BotDB(path)
    return KiskisStore(path)


def balance(store: KiskisStore, user_id: int = 1) -> Any:
    with closing(store.connect()) as conn:
        row = conn.execute(
            "SELECT * FROM roll_hussars WHERE user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def make_context(store: KiskisStore) -> Any:
    return cast(
        Any,
        SimpleNamespace(
            bot_data={"kiskis_store": store},
            bot=AsyncMock(),
            job_queue=SimpleNamespace(run_once=Mock()),
        ),
    )


def test_persistent_personal_and_chat_cooldowns(store: KiskisStore):
    assert store.claim(-1, ALICE.to_dict(), NOW)[0] == "ok"
    assert store.claim(-1, BOB.to_dict(), NOW + 59)[0] == "chat"
    assert store.claim(-1, BOB.to_dict(), NOW + 60)[0] == "ok"
    reopened = KiskisStore(store.path)
    assert reopened.claim(-2, ALICE.to_dict(), NOW + 3600)[0] == "personal"
    assert reopened.claim(-1, ALICE.to_dict(), NOW + DAY)[0] == "ok"
    with closing(store.connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM kiskis_users").fetchone()[0] == 2


def test_streak_persistence_reset_and_chat_isolation(store: KiskisStore):
    assert store.register_attempt(-1, 1, NOW) == 1
    assert store.register_attempt(-1, 1, NOW + 1) == 2
    reopened = KiskisStore(store.path)
    assert reopened.register_attempt(-1, 1, NOW + 2) == 3
    assert reopened.register_attempt(-1, 1, NOW + 3) == 3
    assert reopened.register_attempt(-2, 1, NOW + 4) == 1
    assert reopened.register_attempt(-1, 2, NOW + 5) == 1
    assert reopened.register_attempt(-1, 1, NOW + 6) == 1
    assert reopened.register_attempt(-1, 1, NOW + 6 + DAY) == 1


def test_shared_pause_preserves_attempt_but_not_spam_immunity(store: KiskisStore):
    store.claim(-1, BOB.to_dict(), NOW)
    context = make_context(store)
    context.bot.get_chat_member.return_value = SimpleNamespace(status="member")
    command = SimpleNamespace(message_id=10, sender_chat=None, reply_text=AsyncMock())
    update = cast(
        Any,
        SimpleNamespace(
            effective_user=ALICE, effective_chat=SimpleNamespace(id=-1), message=command
        ),
    )
    with (
        patch("skills.kiskis.random.choices", return_value=["ignore"]),
        patch("skills.kiskis.time.time", return_value=NOW + 20),
        patch("skills.kiskis.cleanup_queue_update"),
    ):
        asyncio.run(kiskis(update, context))
        assert "Подожди 40 сек." in command.reply_text.await_args.args[0]
        asyncio.run(kiskis(update, context))
        assert "зашиплю" in command.reply_text.await_args.args[0]
        context.bot.restrict_chat_member.assert_not_awaited()
        asyncio.run(kiskis(update, context))
        assert "Ш-ш-ш" in command.reply_text.await_args.args[0]
    context.bot.restrict_chat_member.assert_awaited_once()
    assert store.claim(-1, ALICE.to_dict(), NOW + 60)[0] == "ok"


def test_third_call_hisses_without_reward_or_daily_claim(store: KiskisStore):
    context = make_context(store)
    context.bot.get_chat_member.return_value = SimpleNamespace(
        status="member", user=BOB
    )
    command = SimpleNamespace(message_id=10, sender_chat=None, reply_text=AsyncMock())
    update = cast(
        Any,
        SimpleNamespace(
            effective_user=ALICE, effective_chat=SimpleNamespace(id=-1), message=command
        ),
    )
    with (
        patch("skills.kiskis.random.choices", return_value=["ignore"]) as choose,
        patch("skills.kiskis.time.time", return_value=NOW),
        patch("skills.kiskis.cleanup_queue_update") as cleanup,
    ):
        asyncio.run(kiskis(update, context))
        asyncio.run(kiskis(update, context))
        assert "зашиплю" in command.reply_text.await_args.args[0]
        context.bot.restrict_chat_member.assert_not_awaited()
        asyncio.run(kiskis(update, context))
        assert choose.call_count == 2
        assert "Ш-ш-ш" in command.reply_text.await_args.args[0]
        assert cleanup.call_args.args[-1] == 120
    context.bot.restrict_chat_member.assert_awaited_once()
    assert (
        context.bot.restrict_chat_member.await_args.kwargs["until_date"].timestamp()
        == NOW + 300
    )
    assert balance(store) is None
    with closing(store.connect()) as conn:
        assert (
            conn.execute(
                "SELECT last_call FROM kiskis_users WHERE user_id=1"
            ).fetchone()[0]
            == NOW
        )


def test_reward_adds_seconds_without_fake_rolls(store: KiskisStore):
    for instant in (NOW, NOW + DAY):
        assert (
            store.claim(-1, ALICE.to_dict(), instant, reward=ALICE.to_dict())[0] == "ok"
        )
    result = balance(store)
    assert result["total_time_in_club"] == 2 * DAY
    assert (result["shot_counter"], result["dead_counter"], result["miss_counter"]) == (
        0,
        0,
        0,
    )
    assert (
        store.claim(-1, ALICE.to_dict(), NOW + DAY + 1, reward=ALICE.to_dict())[0]
        == "personal"
    )
    assert balance(store)["total_time_in_club"] == 2 * DAY


def test_simultaneous_claims_only_reward_once(store: KiskisStore):
    def claim(_: int):
        return store.claim(-1, ALICE.to_dict(), NOW, reward=ALICE.to_dict())[0]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(claim, range(8)))
    assert results.count("ok") == 1
    assert balance(store)["total_time_in_club"] == DAY


def prepare_food(store: KiskisStore):
    store.claim(
        -1,
        ALICE.to_dict(),
        NOW,
        food={"token": "a" * 32, "preferred": "wet", "command_id": 10},
    )
    store.bind_food("a" * 32, 11)


def test_food_survives_restart_and_rejects_foreign_clicks(store: KiskisStore):
    prepare_food(store)
    reopened = KiskisStore(store.path)
    assert len(reopened.pending_food()) == 1
    args: dict[str, Any] = {"chat_id": -1, "message_id": 11, "selected": "wet"}
    assert reopened.finish_food("a" * 32, NOW + 1, user_id=2, **args)[0] == "foreign"
    assert reopened.finish_food("a" * 32, NOW + 2, user_id=1, **args)[0] == "fed"
    assert reopened.finish_food("a" * 32, NOW + 3, user_id=1, **args)[0] == "done"
    assert balance(store)["total_time_in_club"] == DAY
    assert not reopened.pending_food()


@pytest.mark.parametrize(
    "elapsed,selected,expected",
    [
        (119, "dry", "wrong_food"),
        (120, "wet", "expired"),
        (120, None, "expired"),
        (119, None, "pending"),
    ],
)
def test_food_deadline_and_wrong_answer(
    store: KiskisStore, elapsed: int, selected: str | None, expected: str
):
    prepare_food(store)
    assert store.finish_food("a" * 32, NOW + elapsed, selected=selected)[0] == expected
    assert balance(store) is None


@pytest.mark.parametrize("outcome", list(WEIGHTS))
def test_command_outcomes_and_cleanup(store: KiskisStore, outcome: str):
    if outcome == "other":
        store.claim(-1, BOB.to_dict(), NOW - 61)
    context = make_context(store)
    context.bot.get_chat_member.return_value = SimpleNamespace(
        status="member", user=BOB
    )
    command = SimpleNamespace(message_id=10, sender_chat=None, reply_text=AsyncMock())
    command.reply_text.return_value = SimpleNamespace(message_id=11)
    update = cast(
        Any,
        SimpleNamespace(
            effective_user=ALICE, effective_chat=SimpleNamespace(id=-1), message=command
        ),
    )
    with (
        patch("skills.kiskis.random.choices", return_value=[outcome]),
        patch("skills.kiskis.time.time", return_value=NOW),
        patch("skills.kiskis.cleanup_queue_update") as cleanup,
    ):
        asyncio.run(kiskis(update, context))
    command.reply_text.assert_awaited_once()
    if outcome == "other":
        reply = command.reply_text.await_args
        assert reply.kwargs["parse_mode"] == "HTML"
        assert ALICE.mention_html() in reply.args[0]
        assert BOB.mention_html() in reply.args[0]
    if outcome == "food":
        assert store.pending_food()[0]["message_id"] == 11
        context.job_queue.run_once.assert_called_once()
        cleanup.assert_not_called()
    else:
        assert cleanup.call_args.args[-1] == 120
    if outcome in ("scratch", "sleep"):
        call = context.bot.restrict_chat_member.await_args
        assert call.kwargs["until_date"].timestamp() == NOW + (
            DAY if outcome == "scratch" else 300
        )
    else:
        context.bot.restrict_chat_member.assert_not_awaited()
    if outcome in ("lick", "other"):
        assert (
            balance(store, 2 if outcome == "other" else 1)["total_time_in_club"] == DAY
        )
    else:
        assert balance(store) is None


def test_callback_edits_and_rewards_once(store: KiskisStore):
    prepare_food(store)
    context = make_context(store)
    query = SimpleNamespace(
        data="kiskis:" + "a" * 32 + ":wet",
        from_user=ALICE,
        message=Message(11, datetime.now(), Chat(-1, "supergroup")),
        answer=AsyncMock(),
    )
    with patch("skills.kiskis.time.time", return_value=NOW + 1):
        asyncio.run(feed(cast(Any, SimpleNamespace(callback_query=query)), context))
        asyncio.run(feed(cast(Any, SimpleNamespace(callback_query=query)), context))
    context.bot.edit_message_text.assert_awaited_once()
    assert balance(store)["total_time_in_club"] == DAY
    assert context.job_queue.run_once.call_args.args[1] == 120


def test_expiration_job_and_startup_recovery(store: KiskisStore):
    prepare_food(store)
    context = make_context(store)
    context.add_handler = Mock()
    with (
        patch("skills.kiskis.db", db_path=store.path),
        patch("skills.kiskis.time.time", return_value=NOW + 10),
    ):
        add_kiskis(context, 1)
    assert context.job_queue.run_once.call_args.args[1] == 110
    context.job = SimpleNamespace(data="a" * 32)
    with patch("skills.kiskis.time.time", return_value=NOW + 120):
        asyncio.run(expire_food(context))
    assert not store.pending_food()
    assert balance(store) is None
    assert "поел у соседей" in context.bot.edit_message_text.await_args.args[0]


def test_mute_failure_does_not_create_hussar(store: KiskisStore):
    context = make_context(store)
    context.bot.get_chat_member.side_effect = BadRequest("not enough rights")
    assert not asyncio.run(restrict(context, -1, 1, 300))
    assert balance(store) is None


def test_short_mute_does_not_shorten_existing_restriction(store: KiskisStore):
    context = make_context(store)
    for until in (0, NOW + DAY):
        context.bot.get_chat_member.return_value = SimpleNamespace(
            status="restricted", until_date=datetime.fromtimestamp(until, timezone.utc)
        )
        with patch("skills.kiskis.time.time", return_value=NOW):
            assert asyncio.run(restrict(context, -1, 1, 300))
    context.bot.restrict_chat_member.assert_not_awaited()


def test_timeout_retries_once_with_same_deadline(store: KiskisStore):
    context = make_context(store)
    context.bot.get_chat_member.return_value = SimpleNamespace(status="member")
    context.bot.restrict_chat_member.side_effect = [TimedOut(), True]
    with (
        patch("skills.kiskis.time.time", return_value=NOW),
        patch("skills.kiskis.cleanup_queue_update") as cleanup,
    ):
        assert asyncio.run(restrict(context, -1, 1, 300)) is True
    calls = context.bot.restrict_chat_member.await_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["until_date"] == calls[1].kwargs["until_date"]
    context.bot.send_message.assert_awaited_once()
    assert cleanup.call_args.args[-1] == 120
    assert balance(store) is None


def test_two_timeouts_return_unknown_even_if_notice_fails(store: KiskisStore):
    context = make_context(store)
    context.bot.get_chat_member.side_effect = TimedOut()
    context.bot.send_message.side_effect = TimedOut()
    assert asyncio.run(restrict(context, -1, 1, 300)) is None
    assert context.bot.get_chat_member.await_count == 2


@pytest.mark.parametrize(
    "role,reason", [("administrator", "админов"), ("creator", "владельца")]
)
def test_hiss_precedes_separate_admin_explanation(
    store: KiskisStore, role: str, reason: str
):
    store.register_attempt(-1, ALICE.id, NOW)
    store.register_attempt(-1, ALICE.id, NOW)
    context = make_context(store)
    context.bot.get_chat_member.return_value = SimpleNamespace(status=role)
    command = SimpleNamespace(message_id=10, sender_chat=None, reply_text=AsyncMock())
    update = cast(
        Any,
        SimpleNamespace(
            effective_user=ALICE, effective_chat=SimpleNamespace(id=-1), message=command
        ),
    )
    order = Mock()
    order.attach_mock(command.reply_text, "scene")
    order.attach_mock(context.bot.get_chat_member, "lookup")
    order.attach_mock(context.bot.send_message, "explanation")
    with (
        patch("skills.kiskis.time.time", return_value=NOW),
        patch("skills.kiskis.cleanup_queue_update") as cleanup,
    ):
        asyncio.run(kiskis(update, context))
    assert [call[0] for call in order.mock_calls] == ["scene", "lookup", "explanation"]
    assert "Ш-ш-ш" in command.reply_text.await_args.args[0]
    assert "Telegram" not in command.reply_text.await_args.args[0]
    assert reason in context.bot.send_message.await_args.args[1]
    context.bot.restrict_chat_member.assert_not_awaited()
    assert cleanup.call_count == 2
    assert all(call.args[-1] == 120 for call in cleanup.call_args_list)


def test_retry_detects_mute_applied_before_timeout(store: KiskisStore):
    context = make_context(store)
    context.bot.get_chat_member.side_effect = [
        SimpleNamespace(status="member"),
        SimpleNamespace(
            status="restricted",
            until_date=datetime.fromtimestamp(NOW + 300, timezone.utc),
        ),
    ]
    context.bot.restrict_chat_member.side_effect = TimedOut()
    with (
        patch("skills.kiskis.time.time", return_value=NOW),
        patch("skills.kiskis.cleanup_queue_update"),
    ):
        assert asyncio.run(restrict(context, -1, 1, 300)) is True
    context.bot.restrict_chat_member.assert_awaited_once()
