import logging

from telegram.ext import run_async, CommandHandler, Updater

logger = logging.getLogger(__name__)


def add_core_handlers(upd: Updater, core_handlers_group: int):
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("start", start), core_handlers_group)
    dp.add_handler(CommandHandler("help", help_), core_handlers_group)


@run_async
def start(update, context):
    update.message.reply_text("I'm a VLDC Bot. 😼\n\n"
                              "My source: https://github.com/egregors/vldc-bot")


@run_async
def help_(update, context):
    """ List of ALL commands """
    update.message.reply_text(
        "The bot should be an admin with all admins permissions\n\n"
        "Skills (for admins):\n"
        "SmileMode: allows only not text messages (stickers, GIFs)\n"
        "`/smile_mode_on` – smile mode ON\n"
        "`/smile_mode_off` – smile mode OFF\n"
        "\n\n"
        "Skills (for all):\n"
        "🤔 nothing yet, suggest something!\n"
        "https://github.com/egregors/vldc-bot/issues\n"
        "\n\n"
        "Passive:\n"
        "TowelMode: required reply from new users otherwise blacklisted them\n"
        "TowelMode is ON by default\n"
    )


def error(update, context):
    """ Log Errors caused by Updates """
    logger.warning('Update "%s" caused error "%s"', update, context.error)
