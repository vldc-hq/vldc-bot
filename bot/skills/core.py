import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext

logger = logging.getLogger(__name__)


def add_core(upd: Updater, core_handlers_group: int):
    logger.info("register smile-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("start", start, run_async=True), core_handlers_group)
    dp.add_handler(CommandHandler("help", help_, run_async=True), core_handlers_group)


def start(update: Update):
    update.message.reply_text(
        "I'm a VLDC Bot. 😼\n\n" "My source: https://github.com/vldc-hq/vldc-bot"
    )


def help_(update: Update):
    """List of ALL commands"""
    update.message.reply_text(
        "The bot should be an admin with all admins permissions\n\n"
        "Skills for admins:\n\n"
        "SmileMode: allows only not text messages (stickers, GIFs)\n"
        "`/smile_mode_on` – smile mode ON\n"
        "`/smile_mode_off` – smile mode OFF\n"
        "\n"
        "Version: just version\n"
        "`/version` – show current version of the bot\n"
        "\n\n"
        "Skills for all:\n\n"
        "SinceMode: when the last time we ware discuss this topic?\n"
        "`/since TOPIC` – update topic counter\n"
        "`/since_list` – list off all hot topics\n"
        "for example:\n"
        "   >>> alice: нет, ну современный пхп вполне нормальный язык\n"
        "   >>> bob: /since современный пыхыпы\n"
        "   >>> Nayn: 0 days without «современный пыхыпы»! Already was discussed 47 times\n"
        "   >>> alice: -__-\n"
        "\n\n"
        "Passive:\n"
        "TowelMode: required reply from new users otherwise blacklisted them\n"
        "TowelMode is ON by default\n\n"
        "Feel free to add more stuff!\n"
        "\nhttps://github.com/vldc-hq/vldc-bot/issues\n"
        "\n\n"
    )


def error(update: Update, context: CallbackContext):
    """Log Errors caused by Updates"""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
