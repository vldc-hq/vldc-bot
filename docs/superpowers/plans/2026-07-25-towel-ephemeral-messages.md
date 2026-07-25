# Towel Ephemeral Messages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send the towel challenge and validation hints as Telegram ephemeral
messages to the newly joined human while keeping the successful welcome public.

**Architecture:** Keep the existing towel handler and SQLite quarantine model.
Use `python-telegram-bot` forward compatibility to pass `receiver_user_id`
through `api_kwargs`, and read incoming `ephemeral_message_id` from
`Message.api_kwargs`. Keep the existing public path for bot accounts because
Telegram only supports arbitrary ephemeral delivery to non-bot members.

**Tech Stack:** Python 3.14.2, python-telegram-bot 22.6, unittest/pytest, uv,
SQLite.

## Global Constraints

- Do not upgrade `python-telegram-bot` or change `uv.lock`.
- Do not change quarantine duration, spam classification, callback text,
  database schema, or ban scheduling.
- The towel challenge and short-response feedback must be visible only to the
  selected human and the bot.
- The successful `Добро пожаловать в VLDC!` message must remain public.
- Do not store ephemeral regular `message_id` value `0` for cleanup.
- Preserve cleanup of regular message IDs already stored before deployment.
- Preserve the current public towel path for bot accounts.

---

## File Structure

- Create `bot/tests/towel_mode_test.py` for focused asynchronous towel behavior
  tests.
- Modify `bot/skills/towel_mode.py` only at the challenge send and quarantined
  reply decision points.
- Keep `bot/db/sqlite.py`, dependencies, and configuration unchanged.

### Task 1: Send the Human Challenge Ephemerally

**Files:**

- Create: `bot/tests/towel_mode_test.py`
- Modify: `bot/skills/towel_mode.py:113-154`

**Interfaces:**

- Consumes: `User.is_bot`, `User.id`, `Bot.send_message`, and
  `Bot.send_message(..., api_kwargs={...})`.
- Produces: `quarantine_user(user, chat_id, context)` with separate human and
  bot delivery paths.

- [ ] **Step 1: Write the failing human challenge test**

Create `bot/tests/towel_mode_test.py` with:

```python
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

        database.add_quarantine_user.assert_called_once_with(
            USER_ID, QUARANTINE_TIME
        )
        send_call = bot.send_message.await_args
        self.assertEqual(send_call.args[0], CHAT_ID)
        self.assertEqual(
            send_call.kwargs["api_kwargs"], {"receiver_user_id": USER_ID}
        )
        database.add_quarantine_rel_message.assert_not_called()
        bot.get_me.assert_not_awaited()
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelChallengeTest::test_human_gets_ephemeral_challenge -q
```

Expected: FAIL because `send_message` has no `api_kwargs` entry and
`add_quarantine_rel_message` receives message ID `0`.

- [ ] **Step 3: Implement the separate human and bot challenge paths**

Replace `quarantine_user` in `bot/skills/towel_mode.py` with:

```python
async def quarantine_user(user: User, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    logger.info("put %s in quarantine", user)
    sqlite_db.add_quarantine_user(user.id, QUARANTINE_TIME)

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(choice(I_AM_BOT), callback_data=MAGIC_NUMBER)]]
    )
    challenge = (
        f"{user.name} НЕ нажимай на кнопку ниже, чтобы доказать, что ты не бот.\n"
        "Просто ответь (reply) на это сообщение, кратко написав о себе (у нас так принято).\n"
        "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
        f"А коли не сделаешь, через {QUARANTINE_TIME} минут выкину из чата.\n"
        "Ничего личного, просто боты одолели.\n"
    )

    if not user.is_bot:
        await context.bot.send_message(
            chat_id,
            challenge,
            reply_markup=markup,
            api_kwargs={"receiver_user_id": user.id},
        )
        return

    message_id = (
        await context.bot.send_message(
            chat_id,
            challenge,
            reply_markup=markup,
        )
    ).message_id
    sqlite_db.add_quarantine_rel_message(user.id, message_id)

    bot_user = await context.bot.get_me()
    if user.id == bot_user.id:
        message_id = (
            await context.bot.send_message(
                chat_id,
                "Я простой бот из Владивостока.\n"
                "В-основном занимаюсь тем, что бросаю полотенца в новичков.\n"
                "Увлекаюсь переписыванием себя на раст, но на это постоянно не хватает времени.\n",
                reply_to_message_id=message_id,
            )
        ).message_id

        sqlite_db.delete_quarantine_user(user_id=user.id)
        await context.bot.send_message(
            chat_id, "Добро пожаловать в VLDC!", reply_to_message_id=message_id
        )
```

- [ ] **Step 4: Run the human test and verify GREEN**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelChallengeTest::test_human_gets_ephemeral_challenge -q
```

Expected: `1 passed`.

- [ ] **Step 5: Add the bot compatibility test**

Append to `TowelChallengeTest`:

```python
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
```

- [ ] **Step 6: Run the challenge tests**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelChallengeTest -q
```

Expected: `2 passed`.

- [ ] **Step 7: Format and commit the challenge behavior**

Run:

```bash
uv run black bot/skills/towel_mode.py bot/tests/towel_mode_test.py
git add bot/skills/towel_mode.py bot/tests/towel_mode_test.py
git commit -m "Send towel challenge ephemerally"
```

### Task 2: Process Ephemeral Towel Responses

**Files:**

- Modify: `bot/tests/towel_mode_test.py`
- Modify: `bot/skills/towel_mode.py:164-216`

**Interfaces:**

- Consumes: `Message.api_kwargs`, `Message.text`, SQLite quarantine records,
  `is_worthy`, and `_delete_user_rel_messages`.
- Produces: `catch_reply(update, context)` that validates only ephemeral towel
  responses, sends private short-response feedback, keeps public message
  deletion, and posts a public success message.

- [ ] **Step 1: Import `catch_reply` and write the failing short-response test**

Add `catch_reply` to the import from `skills.towel_mode`, then append:

```python
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
        self.assertEqual(
            send_call.kwargs["api_kwargs"], {"receiver_user_id": USER_ID}
        )
        database.add_quarantine_rel_message.assert_not_called()
```

- [ ] **Step 2: Run the short-response test and verify RED**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelReplyTest::test_short_ephemeral_reply_gets_private_feedback -q
```

Expected: FAIL because the current handler calls regular `delete_message` with
message ID `0` and does not send ephemeral feedback.

- [ ] **Step 3: Add minimal short ephemeral response handling**

After the quarantine lookup and `user is None` return in `catch_reply`, add:

```python
    if "ephemeral_message_id" in update.effective_message.api_kwargs:
        text = update.effective_message.text or ""
        if len(text) < 15:
            await context.bot.send_message(
                update.effective_chat.id,
                f"{update.effective_user.name}, твой ответ слишком короткий. "
                "Я верю, что ты можешь написать больше о себе!",
                api_kwargs={"receiver_user_id": user_id},
            )
            return
```

- [ ] **Step 4: Run the short-response test and verify GREEN**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelReplyTest::test_short_ephemeral_reply_gets_private_feedback -q
```

Expected: `1 passed`.

- [ ] **Step 5: Write the failing valid-response test**

Append to `TowelReplyTest`:

```python
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
        bot.send_message.assert_awaited_once_with(
            CHAT_ID, "Добро пожаловать в VLDC!"
        )
```

- [ ] **Step 6: Run the valid-response test and verify RED**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py::TowelReplyTest::test_valid_ephemeral_reply_gets_public_welcome -q
```

Expected: FAIL because the current handler treats the ephemeral message as a
non-reply and deletes regular message ID `0`.

- [ ] **Step 7: Add the existing public deletion regression test**

Append to `TowelReplyTest`:

```python
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
```

- [ ] **Step 8: Replace the reply-to-public-message flow with the final ephemeral flow**

Replace the conditional block after the quarantine lookup in `catch_reply` with:

```python
    if "ephemeral_message_id" in update.effective_message.api_kwargs:
        text = update.effective_message.text or ""
        if len(text) < 15:
            await context.bot.send_message(
                update.effective_chat.id,
                f"{update.effective_user.name}, твой ответ слишком короткий. "
                "Я верю, что ты можешь написать больше о себе!",
                api_kwargs={"receiver_user_id": user_id},
            )
        elif is_worthy(text):
            await _delete_user_rel_messages(update.effective_chat.id, user_id, context)
            sqlite_db.delete_quarantine_user(user_id=cast(int, user["_id"]))
            await context.bot.send_message(
                update.effective_chat.id, "Добро пожаловать в VLDC!"
            )
        return

    await context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
    )
```

- [ ] **Step 9: Run all towel tests and verify GREEN**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py -q
```

Expected: `5 passed`.

- [ ] **Step 10: Format and commit the response behavior**

Run:

```bash
uv run black bot/skills/towel_mode.py bot/tests/towel_mode_test.py
git add bot/skills/towel_mode.py bot/tests/towel_mode_test.py
git commit -m "Handle ephemeral towel replies"
```

### Task 3: Verify the Outward Contract and Branch

**Files:**

- Verify: `bot/skills/towel_mode.py`
- Verify: `bot/tests/towel_mode_test.py`
- Verify: `docs/superpowers/specs/2026-07-25-towel-ephemeral-messages-design.md`
- Verify: `docs/superpowers/plans/2026-07-25-towel-ephemeral-messages.md`

**Interfaces:**

- Consumes: completed implementation and repository CI commands.
- Produces: a clean feature branch ready to push and open as a draft pull
  request against `vldc-hq/vldc-bot:master`.

- [ ] **Step 1: Run the focused behavior tests**

Run:

```bash
PYTHONPATH=./bot uv run pytest bot/tests/towel_mode_test.py -q
```

Expected: `5 passed`.

- [ ] **Step 2: Run the complete test suite**

Run:

```bash
uv run make test
```

Expected: all tests pass with zero failures.

- [ ] **Step 3: Run all project linters**

Run:

```bash
uv run make lint
```

Expected: Black, Pylint, Flake8, Mypy, and Pyright all exit successfully.

- [ ] **Step 4: Verify patch hygiene and branch scope**

Run:

```bash
git diff --check upstream/master...HEAD
git status -sb
git log --oneline upstream/master..HEAD
```

Expected: no whitespace errors, a clean working tree, and only the design,
plan, challenge, and reply commits on
`agent/towel-ephemeral-messages`.

- [ ] **Step 5: Push and open the draft pull request**

Run:

```bash
git push -u origin agent/towel-ephemeral-messages
```

Then create a draft pull request:

- Base repository: `vldc-hq/vldc-bot`
- Base branch: `master`
- Head repository and branch:
  `getjump/vldc-bot:agent/towel-ephemeral-messages`
- Title: `Send towel mode messages ephemerally`
- Body: summarize the private challenge and feedback, the public welcome,
  `api_kwargs` forward compatibility, the `message_id = 0` cleanup fix, and the
  exact test and lint commands run.
