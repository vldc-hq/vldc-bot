# Towel Ephemeral Messages Design

## Goal

Move the towel challenge and personal validation feedback to Telegram ephemeral
messages so that only the newly joined human and the bot can see them. Keep the
final `Добро пожаловать в VLDC!` message visible to the whole group.

## Current Behavior

`catch_new_user` adds every new member to the SQLite quarantine and calls
`quarantine_user`. The function sends a normal group message with the towel
instructions and an inline callback button, then stores its regular message ID
for later cleanup.

While a member is quarantined, `catch_reply` deletes public messages unless the
message is a reply to the bot. A sufficiently long and valid reply removes the
member from quarantine and posts a public welcome.

## Telegram API Constraints

Telegram Bot API supports ephemeral group messages through
`receiver_user_id`. Such messages are visible only to the selected non-bot user
and the bot.

An ephemeral message has regular `message_id` equal to `0` and a separate
`ephemeral_message_id`. It must not be deleted through the regular
`deleteMessage` method.

The project uses `python-telegram-bot` 22.6, which predates native ephemeral
message fields. Its forward-compatibility contract supports:

- sending `receiver_user_id` through `Bot.send_message(..., api_kwargs={...})`;
- reading unknown incoming fields through `Message.api_kwargs`.

No dependency upgrade is required.

## Design

### Sending the challenge

For a human member, `quarantine_user` sends the existing towel text and inline
button to the group chat with:

```python
api_kwargs={"receiver_user_id": user.id}
```

The ephemeral response's regular `message_id` is not added to
`towel_quarantine.rel_messages`. Existing stored regular message IDs remain
supported so deployments can clean up messages created before this change.

Telegram permits arbitrary ephemeral messages only to non-bot members. Bot
accounts therefore retain the current public challenge path, including the
existing self-introduction when the joining bot is VLDC bot itself.

### Processing member messages

`catch_reply` considers a message ephemeral when
`"ephemeral_message_id" in update.effective_message.api_kwargs`.

For an ephemeral message from a quarantined member:

- a response shorter than 15 characters remains rejected, but is not passed to
  regular `delete_message`; the feedback is sent ephemerally to that member;
- a valid response removes the member from quarantine and sends
  `Добро пожаловать в VLDC!` as a new public group message without replying to
  the ephemeral message;
- a response rejected by the spam check leaves the member quarantined and
  produces no public message.

For a normal group message from a quarantined member, the existing deletion
behavior remains in place. A normal public reply is not accepted as the towel
response because the challenge and response are intended to remain private.

The inline callback continues to use `answer_callback_query` with
`show_alert=True`, which is already visible only to the user who pressed it.

### Failure behavior

The bot must be a group administrator to send an arbitrary ephemeral message to
a newly joined member. Towel mode already relies on administrator rights to ban
members after the quarantine timeout.

There is no public-message fallback when ephemeral sending fails because that
would violate the privacy requirement. The existing fail-closed quarantine
behavior remains unchanged.

Telegram does not guarantee delivery of an ephemeral message, especially when
the recipient is offline. This is an API limitation; successful delivery cannot
be confirmed by the bot.

## State and Contract Invariants

- Each newly joined human is placed in quarantine exactly once.
- Each human receives a separate ephemeral challenge, including when several
  members join in one service update.
- No ephemeral `message_id` is stored as a regular related message.
- Public messages from quarantined users continue to be deleted.
- Only a valid ephemeral response removes the human from quarantine.
- The successful welcome remains public and does not reply to an ephemeral
  message ID.
- Ban scheduling and existing SQLite schema remain unchanged.

## Testing

Add focused asynchronous unit tests for `towel_mode`:

1. A human challenge includes `receiver_user_id` and does not persist regular
   message ID `0`.
2. A bot account keeps the existing public challenge behavior.
3. A short ephemeral response sends private feedback and never calls regular
   `delete_message` for ID `0`.
4. A valid ephemeral response removes the member from quarantine and sends a
   public welcome without `receiver_user_id`.
5. A normal message from a quarantined member is still deleted.

Run the focused towel tests first, then the full test and lint commands used by
CI:

```bash
uv run pytest bot/tests/towel_mode_test.py
uv run make test
uv run make lint
```

## Non-Goals

- Upgrading `python-telegram-bot`.
- Making unrelated bot commands ephemeral.
- Changing quarantine duration, spam classification, callback text, database
  schema, or ban scheduling.
- Adding a public fallback for clients that do not display the ephemeral
  message.

## References

- Telegram Bot API:
  https://core.telegram.org/bots/api#ephemeral-messages-and-commands
- python-telegram-bot forward compatibility:
  https://github.com/python-telegram-bot/python-telegram-bot/wiki/Bot-API-Forward-Compatibility
