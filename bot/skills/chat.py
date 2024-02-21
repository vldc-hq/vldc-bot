import random
import logging
import re
from collections import deque
from datetime import datetime, timedelta
from threading import Lock

import openai
from config import get_group_chat_id, get_config
from mode import Mode, ON
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, Updater
from telegram.ext.filters import Filters


# Max number of messages to keep in memory.
MAX_MESSAGES = 100
# Max age of message to be considered for poem generation.
MAX_AGE = timedelta(hours=6)
# Number of examples to show in the prompt.
NUM_EXAMPLES = 10
# How often muse visits Nyan.
SLEEP_INTERVAL = 60 * 60
# Number of poems per day.
POEMS_PER_DAY = 2


logger = logging.getLogger(__name__)

mode = Mode(mode_name="chat_mode", default=ON)


class Nyan:
    def __init__(self):
        self.memory = deque(maxlen=MAX_MESSAGES)
        self.lock = Lock()

    def registerMessage(self, update: Update, context: CallbackContext):
        if update.message is None:
            return
        if update.message.text.startswith("/"):
            return
        with self.lock:
            self.memory.append(
                (
                    datetime.now(),
                    f"{update.effective_user.full_name}: {update.message.text}",
                ),
            )

    def forget(self):
        with self.lock:
            self.memory.clear()

    def write_a_poem(self) -> str:
        log = []
        with self.lock:
            for dt, message in self.memory:
                if datetime.now() - dt > MAX_AGE:
                    continue
                log.append(message)
        if len(log) < 10:
            return ""

        theme = summarize("\n".join(log))
        examples = get_examples(NUM_EXAMPLES)

        prompt = f"""You are a telegram chat bot for a Vladivostok Developers Community (VLDC).
        You are written in python, and shy about it (your dream is to be rewritten in Rust).
        Your name is Nyan and your avatar is a pixelized orange cat with tiger stripes.
        You are master of short funny poems in a specific style called пирожки.
        This style uses poetic meter iambic tetrameter with syllable count 9-8-9-8
        without rhyming, punctuation marks, or capitalization.
        Пирожок is always 4 lines long and has a humorous punchline.
        Here are some examples of your work:

        {examples}
        """

        prompt_user = f"""Please write one 4 line long пирожок about the following topic: {theme}."""

        response = openai.chat.completions.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": prompt_user,
                },
            ],
            temperature=0.5,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
        )

        return response.choices[0].message.content


nyan = Nyan()


@mode.add
def add_chat_mode(upd: Updater, handlers_group: int):
    global PIROZHKI
    try:
        with open("/app/pirozhki.txt", "rt", encoding="utf8") as fi:
            PIROZHKI = fi.read().splitlines()
    except:  # noqa: E722
        logger.error("failed to read pirozhki!")

    logger.info("registering chat handlers")
    dp = upd.dispatcher
    dp.add_handler(
        MessageHandler(
            Filters.chat(username=get_group_chat_id().strip("@"))
            & Filters.text
            & ~Filters.status_update,
            nyan_listen,
            run_async=True,
        ),
        handlers_group,
    )

    # Muse visits Nyan at most twice a day.
    upd.job_queue.run_repeating(
        muse_visit,
        interval=SLEEP_INTERVAL,
        first=SLEEP_INTERVAL,
        context={"chat_id": get_config()["GROUP_CHAT_ID"]},
    )


def nyan_listen(update: Update, context: CallbackContext):
    if update.effective_user.id == context.bot.get_me().id:
        return
    nyan.registerMessage(update, context)


def muse_visit(context: CallbackContext):
    # We want nyan to be visited by muse at random times, but
    # about POEMS_PER_DAY times per day.
    secondsInDay = 24 * 60 * 60
    inspirationRate = float(POEMS_PER_DAY) / float(secondsInDay / SLEEP_INTERVAL)
    if random.random() > inspirationRate:
        return

    try:
        message = nyan.write_a_poem()
        if message != "":
            context.bot.send_message(
                chat_id=context.job.context["chat_id"], text=message
            )
        nyan.forget()
    except Exception as e:  # pylint: disable=broad-except
        logger.error("inspiration did not come: %s", e)


def summarize(log):
    prompt_user = "please summarize the following text in one short sentence:\n" + log
    response = openai.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            # {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": prompt_user,
            },
        ],
        temperature=0.5,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.6,
    )

    return response.choices[0].message.content


def format_pirozhok(pirozhok):
    syllables = [9, 8, 9, 8]
    words = pirozhok.split()
    if len(words) == 0:
        return ""
    lines = []

    for s in syllables:
        cnt = 0
        line = []
        while cnt < s:
            word = words.pop(0)
            cnt += len(re.findall(r"[аеёиоуыэюя]", word, re.I))
            line.append(word)
        lines.append(" ".join(line))

    return "\n".join(lines)


def get_examples(n=10):
    poems = []
    while len(poems) < n:
        pirozhok = random.choice(PIROZHKI)
        try:
            formatted = format_pirozhok(pirozhok)
            poems.append(formatted)
        except:
            # Some pirozhki do not match
            None

    return "\n\n".join(poems)


PIROZHKI = [
    "оксана просто постарайся тряси меня еще сильней кричи и не жалей пощёчин возможно я еще живой",
    "глеб управляет президентом особенно по выходным то громче сделает то тише то выключит на полчаса",
    "я робок говорить не мастер пусть всё поведают тебе мой взгляд трепещущее сердце эрекция в конце концов",
    "смотрю на грязные машины газон промокший и тебе пересылаю сообщенья путём почтового дождя",
    "молчу поскольку не желаю произносить ненужных слов а нужные слова ни вами ни мной не изобретены",
    "олег хорошим человеком работает семнадцать лета в отпуск ездит в копенгаген пинать приветливых датчан",
    "как можно столько ошибаться спросил сапера иисус и воскресил его в пять тысяч шестьсот четырнадцатый раз",
    "мы побываем в уникальных доисторических местах где со времён палеозоя не происходит ничего",
    "жене машину покупаю любовнице вино и торт жена когда нибудь узнает и скажет вова молодец",
    "боль отпускала захотелось сначала жить потом дышать потом соседку веру львовну ударить чем нибудь в ответ",
    "шутил патологоанатом так искрометно что олег не выдержал и засмеялся придется снова зашивать",
    "мне нужно чтобы подлечили мой нездоровый похуизм так вам талон к врачу какому да мне ващето похую"
    "аркадию в военкомате велят раздеться до трусов аркадий встал по стойке смирно снимает первые трусы",
    "придет пора меня не станет сказал сантехник михаил и этот кран текущий в ванной пусть будет память обо мне",
    "меня в кружок антагонистов позвали четверо ребят не объяснив мою задачу ничо ващще не объяснив",
    "на чердаке поймали бога он улететь хотел в окно весь перемазанный вареньем похожий чемто на шойгу",
    "петру сегодня восемнадцать ну вот и всё подумал он закончилась пора веселья теперь лишь слёзы горе смерть",
    "толстухе ногу оторвало но есть и в этом позитив ей потерять во сне не снилось за две секунды семь кило",
    "вчера с войны пришол шаинский с одной пластмассовой рукой сел за рояль достал чекушку на нотах сайру разложы",
    "скажите где у вас утесы я вся сгораю от стыда куда скажите можно спрятать мне тело жырное своё",
]
