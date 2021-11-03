import logging
import xml.etree.ElementTree as ET
import requests
from mode import cleanup_queue_update

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

logger = logging.getLogger(__name__)

KOZULA_RATE = 600000
CBR_URL = "https://cbr.ru/scripts/XML_daily.asp"


def add_kozula(upd: Updater, handlers_group: int):
    logger.info("registering tree handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("kozula", kozula, run_async=True), handlers_group)


def kozula(update: Update, context: CallbackContext):
    request = requests.get(CBR_URL)
    root = ET.fromstring(request.content)
    for child in root:
        if child.attrib["ID"] == "R01235":
            usd_rate = float(child.find("Value").text.replace(",", "."))

    logger.info("USD rate: %s", usd_rate)
    kozula_usd = round(KOZULA_RATE / usd_rate, 2)
    kozula_usd_formated = "${:,.2f}".format(kozula_usd)
    kozula_rub_formated = "{:,} ₽".format(KOZULA_RATE).replace(",", " ")

    text = (
        f"Текущий курс Козули в RUB: {kozula_rub_formated}\n"
        f"Текущий курс Козули в USD ~ {kozula_usd_formated}\n"
        f"Курс USD/RUB: {round(usd_rate, 2)}"
    )

    result = context.bot.send_message(update.effective_chat.id, text)
    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        300,
        remove_cmd=True,
        remove_reply=True,
    )
