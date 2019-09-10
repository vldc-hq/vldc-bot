from telegram.ext import run_async


@run_async
def start(update, context):
    update.message.reply_text("I'm a VLDC Bot.\n\n"
                              "My source: https://github.com/egregors/vldc-bot")


@run_async
def help_(update, context):
    """ List of ALL commands """
    update.message.reply_text("The bot should be an admin with all admins permissions\n\n"
                              "'/smile_mode_on' – smile mode ON\n"
                              "'/smile_mode_off' – smile mode OFF\n")

def error(update, context):
    """ Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
