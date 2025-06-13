import logging
import xml.etree.ElementTree as ET
from typing import Optional

import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CallbackContext

from mode import cleanup_queue_update
from handlers import ChatCommandHandler
from utils.cache import timed_lru_cache

logger = logging.getLogger(__name__)

KOZULA_RATE_USD = 15_000
CBR_URL = "https://cbr.ru/scripts/XML_daily.asp"


def add_kozula(application: Application, handlers_group: int):
    logger.info("registering tree handlers")
    application.add_handler(ChatCommandHandler("kozula", kozula), handlers_group)


@timed_lru_cache(ttl=3600)
def _get_usd_rate() -> Optional[float]:
    rate: Optional[float] = None
    try:
        request = requests.get(CBR_URL, timeout=3)
        root = ET.fromstring(request.content)
        for child in root:
            if child.attrib["ID"] == "R01235":
                rate = float(child.find("Value").text.replace(",", "."))
    except requests.exceptions.RequestException as e:
        logger.error("can't get USD rate: %s", e)

    return rate


async def kozula(update: Update, context: CallbackContext):
    usd_rate = _get_usd_rate()
    kozula_rates = [
        (
            f"{round(KOZULA_RATE_USD * usd_rate, 2)}₽"
            if usd_rate is not None
            else "курс ₽ недоступен"
        ),
        f"${KOZULA_RATE_USD}",
    ]

    rates = "\n".join(filter(bool, kozula_rates))
    result = await context.bot.send_message(
        update.effective_chat.id,
        f"Текущий курс Козули: \n{rates}",
    )

    cleanup_queue_update(
        queue=context.job_queue,
        cmd=update.message,
        result=result,
        seconds=300,
        remove_reply=True,
    )
