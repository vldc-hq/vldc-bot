"""Daily cat encounter. No AI calls or changes to roulette mechanics."""

import json
import logging
import math
import random
import time
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, cast

from telegram import (
    Update,
    User,
    Message,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import TelegramError, TimedOut
from telegram.ext import ContextTypes, CallbackQueryHandler, filters

from db.sqlite import db
from db.kiskis import KiskisStore, FOOD_TIMEOUT
from handlers import ChatCommandHandler
from mode import cleanup_queue_update
from typing_utils import App, get_job_queue

logger = logging.getLogger(__name__)
CLEANUP_SECONDS = 120
WEIGHTS = {
    "scratch": 5,
    "lick": 10,
    "other": 5,
    "sleep": 10,
    "food": 10,
    "ignore": 12,
    "prey": 8,
    "cable": 8,
    "rust": 8,
    "fur": 8,
    "box": 8,
    "call": 8,
}
TEXTS = {
    "hiss": "😾 Ш-ш-ш, {name}! С первого раза слышно было. "
    "Пять минут тишины, без гусарских дней.",
    "scratch": "😾 Нян пришёл, {name}. Ты зачем-то потрогал живот. "
    "Сутки зализывать раны, без гусарских дней.",
    "lick": "😽 Подставляй лоб, {name}. Остальные настреляли, ты нализал. "
    "+24 часа гусарства.",
    "other": "🐈 Подвинься, {name}, ты загораживаешь {other}. "
    "Вот кому сутки гусарства. А ты хорошо кискискал, продолжай.",
    "sleep": "💤 Всё, {name}, ты мебель. Пять минут не ёрзай, нян лёг.",
    "food": "🍽️ Так, {name}, нежности потом. Показывай, что в пакетике. "
    "И не дай бог опять вот это.",
    "fed": "😽 Вот можешь же, когда голодный не ты. Подставляй лоб, {name}. "
    "Сейчас налижем тебе сутки гусарства.",
    "wrong_food": "😾 Я это вчера любил, {name}. Вчера. "
    "Пять минут посиди молча, пока я закапываю.",
    "expired": "🐾 Пока ты выбирал, {name}, нян поел у соседей. "
    "Там пакетик открывают без совещания.",
    "ignore": "👂 Два уха повернулись в твою сторону. На этом всё.",
    "prey": "🐁 Положил перед тобой дохлый микросервис. Ещё отвечает на health.",
    "cable": "🔌 Интернет пропал. Ты впервые за день почувствовал покой.",
    "rust": "🦀 Переписал твой проект на Rust. Запустить не смог: у него лапки.",
    "fur": "🧶 Потёрся о {name}. Теперь ты тоже немного кот. "
    "Но жрать всё ещё покупаешь ты.",
    "box": "📦 На, {name}, коробка. Руками не трогай, я в ней. "
    "Глазами тоже аккуратнее.",
    "call": "🗣️ Нян сказал «кс-кс-кс». Ты подошёл. Неловко вышло.",
}


def get_store(context: ContextTypes.DEFAULT_TYPE) -> KiskisStore:
    return context.bot_data["kiskis_store"]


def add_kiskis(app: App, handlers_group: int) -> None:
    app.bot_data["kiskis_store"] = KiskisStore(db.db_path)
    app.add_handler(
        ChatCommandHandler(
            "kiskis", kiskis, filters=filters.ChatType.GROUPS, block=True
        ),
        group=handlers_group,
    )
    app.add_handler(
        CallbackQueryHandler(feed, pattern=r"^kiskis:[a-f0-9]{32}:(wet|dry)$"),
        group=handlers_group,
    )
    if app.job_queue is not None:
        for food in app.bot_data["kiskis_store"].pending_food():
            app.job_queue.run_once(
                expire_food, max(0, food["expires"] - time.time()), data=food["token"]
            )


def wait_text(seconds: float) -> str:
    minutes = math.ceil(seconds / 60)
    return f"{minutes // 60} ч {minutes % 60} мин"


async def restrict(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, seconds: int
) -> bool | str | None:
    # Keep the same deadline on retry: a lost response may hide a successful mute.
    until = int(time.time() + seconds)
    for attempt in range(2):
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status == "creator":
                return (
                    "😿 Лапа не дотянулась: владельца чата Telegram не даёт поцарапать."
                )
            if member.status == "administrator":
                return "😿 Лапа не дотянулась: админов Telegram не даёт поцарапать."
            # Never shorten an existing (or permanent) restriction.
            if member.status == "restricted":
                previous = getattr(member, "until_date", None)
                if previous is not None and (
                    previous.timestamp() == 0 or previous.timestamp() >= until
                ):
                    return True
            await context.bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions.no_permissions(),
                until_date=datetime.fromtimestamp(until, timezone.utc),
            )
            return True
        except TimedOut:
            logger.warning(
                "kiskis restriction timed out for %s (attempt %s)", user_id, attempt + 1
            )
            if attempt == 0:
                await retry_notice(context, chat_id)
        except TelegramError as exc:
            logger.warning("kiskis could not restrict user %s: %s", user_id, exc)
            return False
    return None


async def retry_notice(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    try:
        message = await context.bot.send_message(
            chat_id, "😿 Замахнулся, а лапа зависла. Сейчас попробую ещё раз."
        )
        cleanup_queue_update(get_job_queue(context), None, message, CLEANUP_SECONDS)
    except TelegramError as exc:
        logger.info("kiskis retry notice could not be sent: %s", exc)


def outcome_text(user: User, outcome: str, other: str = "") -> str:
    return TEXTS[outcome].format(name=user.mention_html(), other=other)


async def apply_outcome(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, user: User, outcome: str
) -> None:
    seconds = {"scratch": 86400, "sleep": 300, "wrong_food": 300, "hiss": 300}.get(
        outcome
    )
    if not seconds:
        return
    restricted = await restrict(context, chat_id, user.id, seconds)
    if restricted is True:
        return
    if isinstance(restricted, str):
        text = restricted
    elif restricted is False:
        text = "😿 Лапа не дотянулась: Telegram не дал поцарапать."
    else:
        text = "😿 Лапа опять зависла. Telegram не ответил — не знаю, удалось ли поцарапать."
    message = await context.bot.send_message(chat_id, text)
    cleanup_queue_update(get_job_queue(context), None, message, CLEANUP_SECONDS)


async def kiskis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # pylint: disable=too-many-locals,too-many-branches
    user, chat, command = update.effective_user, update.effective_chat, update.message
    if user is None or user.is_bot or chat is None or command is None:
        return
    if command.sender_chat is not None:
        return
    store = get_store(context)
    attempts = store.register_attempt(chat.id, user.id, time.time())
    if attempts >= 3:
        result = await command.reply_text(outcome_text(user, "hiss"), parse_mode="HTML")
        cleanup_queue_update(get_job_queue(context), command, result, CLEANUP_SECONDS)
        await apply_outcome(context, chat.id, user, "hiss")
        return
    players = store.players(chat.id, user.id)
    # Only previous /kiskis players in this chat are eligible for a gift.
    outcomes = [key for key in WEIGHTS if key != "other" or players]
    outcome = random.choices(outcomes, weights=[WEIGHTS[key] for key in outcomes])[0]
    recipient = None
    if outcome == "other":
        recipient = random.choice(players)
        try:
            member = await context.bot.get_chat_member(chat.id, recipient["id"])
            if member.status in ("left", "kicked") or (
                member.status == "restricted"
                and not getattr(member, "is_member", False)
            ):
                outcome, recipient = "ignore", None
            else:
                recipient = member.user.to_dict()
        except TelegramError:
            outcome, recipient = "ignore", None
    token = uuid4().hex
    food = (
        {
            "token": token,
            "preferred": random.choice(["wet", "dry"]),
            "command_id": command.message_id,
        }
        if outcome == "food"
        else None
    )
    status, remaining = store.claim(
        chat.id,
        user.to_dict(),
        time.time(),
        reward=user.to_dict() if outcome == "lick" else recipient,
        food=food,
    )
    markup = None
    logger.info(
        "kiskis chat=%s user=%s status=%s outcome=%s",
        chat.id,
        user.id,
        status,
        outcome if status == "ok" else "cooldown",
    )
    if status == "personal":
        text = (
            f"😾 Придержи кискискалку, {user.mention_html()}. На сегодня няну тебя "
            f"хватило. Приходи через {wait_text(remaining)}."
        )
    elif status == "chat":
        text = (
            "🐈 По одному. У меня две лапы для обнимашек, остальные для нападения.\n\n"
            f"Нян ещё занят. Подожди {math.ceil(remaining)} сек. "
            "и позови снова: /kiskis. Твоя попытка не потрачена."
        )
    else:
        other = User.de_json(recipient, context.bot) if recipient else None
        text = outcome_text(user, outcome, other.mention_html() if other else "")
        if food:
            markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Влажный корм", callback_data=f"kiskis:{token}:wet"
                        ),
                        InlineKeyboardButton(
                            "Сухой корм", callback_data=f"kiskis:{token}:dry"
                        ),
                    ]
                ]
            )
    if attempts == 2:
        text += "\n😼 Ещё раз подряд позовёшь — зашиплю. И пять минут посидишь молча."
    result = await command.reply_text(text, reply_markup=markup, parse_mode="HTML")
    queue = get_job_queue(context)
    if status == "ok" and food:
        store.bind_food(token, result.message_id)
        if queue is not None:
            queue.run_once(expire_food, FOOD_TIMEOUT, data=token)
    else:
        cleanup_queue_update(queue, command, result, CLEANUP_SECONDS)
    if status == "ok":
        await apply_outcome(context, chat.id, user, outcome)


async def present_food(
    context: ContextTypes.DEFAULT_TYPE, status: str, food: dict[str, Any]
) -> None:
    user = User.de_json(json.loads(food["meta"]), context.bot)
    if food["message_id"] is None:
        return
    text = outcome_text(user, status)
    try:
        await context.bot.edit_message_text(
            text,
            chat_id=food["chat_id"],
            message_id=food["message_id"],
            reply_markup=None,
            parse_mode="HTML",
        )
    except TelegramError as exc:
        logger.warning("kiskis could not edit food message: %s", exc)
    queue = get_job_queue(context)
    if queue is not None:
        queue.run_once(delete_food_messages, CLEANUP_SECONDS, data=food)
    await apply_outcome(context, food["chat_id"], user, status)


async def delete_food_messages(context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.job is None:
        return
    food = cast(dict[str, Any], context.job.data)
    for message_id in (food["message_id"], food["command_id"]):
        try:
            await context.bot.delete_message(food["chat_id"], message_id)
        except TelegramError as exc:
            logger.info("kiskis cleanup skipped: %s", exc)


async def expire_food(context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.job is None:
        return
    status, food = get_store(context).finish_food(str(context.job.data), time.time())
    if food:
        await present_food(context, status, food)


async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not isinstance(query.data, str):
        return
    message = query.message
    if not isinstance(message, Message):
        await query.answer("Миску уже унесли.")
        return
    _, token, selected = query.data.split(":")
    status, food = get_store(context).finish_food(
        token,
        time.time(),
        user_id=query.from_user.id,
        chat_id=message.chat_id,
        message_id=message.message_id,
        selected=selected,
    )
    if status == "foreign":
        await query.answer(
            f"😾 Лапы из чужой миски, {query.from_user.full_name}. "
            "Себе кота накс-кс-кскай."
        )
    elif status == "done":
        await query.answer("😼 Всё, пакетик открыт. Обратно паштет не запихаешь.")
    else:
        try:
            await query.answer()
        except TelegramError as exc:
            logger.info("kiskis callback acknowledgement failed: %s", exc)
        if food:
            await present_food(context, status, food)
