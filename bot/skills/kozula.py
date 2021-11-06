import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from mode import cleanup_queue_update
from utils.cache import timed_lru_cache

logger = logging.getLogger(__name__)

KOZULA_RATE = 600_000
CBR_URL = "https://cbr.ru/scripts/XML_daily.asp"


def add_kozula(upd: Updater, handlers_group: int):
    logger.info("registering tree handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("kozula", kozula, run_async=True), handlers_group)


@timed_lru_cache(ttl=3600)
def _get_usd_rate() -> Optional[float]:
    rate: Optional[float] = None
    try:
        request = requests.get(CBR_URL)
        root = ET.fromstring(request.content)
        for child in root:
            if child.attrib["ID"] == "R01235":
                rate = float(child.find("Value").text.replace(",", "."))
    except requests.exceptions.RequestException as e:
        logger.error("can't get USD rate: %s", e)

    return rate


def kozula(update: Update, context: CallbackContext):
    usd_rate = _get_usd_rate()
    kozula_rates = [
        f"{KOZULA_RATE}₽",
        f"${round(KOZULA_RATE / usd_rate, 2)}" if usd_rate is not None else "",
    ]

    result = context.bot.send_message(
        update.effective_chat.id,
        f"Текущий курс Козули: {' | '.join(filter(bool, kozula_rates))}",
    )

    cleanup_queue_update(
        queue=context.job_queue,
        cmd=update.message,
        result=result,
        seconds=300,
        remove_reply=True,
    )
