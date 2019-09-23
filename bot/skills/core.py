import logging

from telegram import Update
from telegram.ext import run_async, CommandHandler, Updater, CallbackContext

logger = logging.getLogger(__name__)


def add_core_handlers(upd: Updater, core_handlers_group: int):
    logger.info("register smile-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("start", start), core_handlers_group)
    dp.add_handler(CommandHandler("help", help_), core_handlers_group)


@run_async
def start(update: Update, context: CallbackContext):
    update.message.reply_text("I'm a VLDC Bot. 😼\n\n"
                              "My source: https://github.com/egregors/vldc-bot")


@run_async
def help_(update: Update, context: CallbackContext):
    """ List of ALL commands """
    update.message.reply_text(
        "The bot should be an admin with all admins permissions\n\n"

        "Skills for admins:\n"
        "SmileMode: allows only not text messages (stickers, GIFs)\n"
        "`/smile_mode_on` – smile mode ON\n"
        "`/smile_mode_off` – smile mode OFF\n"
        "\n\n"

        "Skills for all:\n"
        "SinceMode: when the last time we ware discuss this topic?\n"
        "`/since TOPIC` – update topic counter\n"
        "`/since_list` – list off all hot topics\n"
        "for example:\n"
        "   >>> alice: нет, ну современный пхп вполне нормальный язык\n"
        "   >>> bob: /since современный пыхыпы\n"
        "   >>> Nayn: 0 days without «современный пыхыпы»! Already was discussed 47 times\n"
        "   >>> alice: -__-\n"
      
        "Version: just version\n"
        "`/version` – show current version of the bot\n\n"
      
        "Feel free to add more stuff!\n"
        "\nhttps://github.com/egregors/vldc-bot/issues\n"
        "\n\n"

        "Passive:\n"
        "TowelMode: required reply from new users otherwise blacklisted them\n"
        "TowelMode is ON by default\n"
    )


def error(update: Update, context: CallbackContext):
    """ Log Errors caused by Updates """
    logger.warning('Update "%s" caused error "%s"', update, context.error)
