import os
from google.cloud import speech
import requests
import logging
import json
import io
from pydub import AudioSegment

TOKEN = os.environ["TOKEN"]
LANG = os.environ["LANG"]
SAMPLE_RATE_HERTZ = os.environ["SAMPLE_RATE_HERTZ"]
ENCODING_TYPE = os.environ["ENCODING_TYPE"]
CHANNEL_COUNT = os.environ["CHANNEL_COUNT"]
ENABLE_AUTOMATIC_PUNCTUATION = os.environ["ENABLE_AUTOMATIC_PUNCTUATION"]


logger = logging.getLogger(__name__)

speechClient = speech.SpeechClient()

def _get_audio_file_data(file_id):
    """
    gets audio file 
    """
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    jsonResponse = response.json()
    logger.info(json.dumps(jsonResponse, indent = 4))
    res = jsonResponse["result"]
    return res

def _get_binnary_content(filename):
    url = f"https://api.telegram.org/file/bot{TOKEN}/{filename}"
    logger.info(f"Get request to {url}")
    response = requests.get(url, stream=True)
    logger.info(f"Response code {response.ok}")
    """Todo: add converting here from .oga to wav"""
    temp = io.BytesIO(response.content)
    voice_data = AudioSegment.from_file(temp.read()).export(format='wav')
    """Todo: add converting here from .oga to wav"""
    return voice_data.read()

def _send_binnary_to_google_speech(content):
    """
    sends binnary data of voice to google speech
    """
    config = {
        "language_code": LANG,
        "sample_rate_hertz": int(SAMPLE_RATE_HERTZ),
        "encoding": ENCODING_TYPE,
        "audio_channel_count": int(CHANNEL_COUNT),
        "enable_automatic_punctuation": bool(ENABLE_AUTOMATIC_PUNCTUATION),
    }
    audio = {"content": content}
    recognized_text = speechClient.recognize(config=config, audio=audio)
    return recognized_text.results

def get_text_from_speech(file_id):
    """
    gets text from voice
    """
    file = _get_audio_file_data(file_id)
    content = _get_binnary_content(file["file_path"])
    res = _send_binnary_to_google_speech(content)
    return res
