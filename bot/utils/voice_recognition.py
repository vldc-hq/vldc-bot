import os
from google.cloud import speech
import requests
import logging
import json
from tempfile import NamedTemporaryFile
import subprocess

TOKEN = os.environ["TOKEN"]

LANG = "ru-RU"
SAMPLE_RATE_HERTZ = 48000
ENCODING_TYPE = "LINEAR16"
CHANNEL_COUNT = 1
ENABLE_AUTOMATIC_PUNCTUATION = True
SPEECH_MODEL = "default"

logger = logging.getLogger(__name__)

speech_client = speech.SpeechClient()


def _get_audio_file_data(file_id):
    """
    gets audio file 
    """
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    json_response = response.json()
    logger.info("Voice data has been obtained", json.dumps(json_response, indent=4))
    res = json_response["result"]
    return res


def _get_binary_content(file):
    file_name = file["file_path"]
    url = f"https://api.telegram.org/file/bot{TOKEN}/{file_name}"
    response = requests.get(url, stream=True)

    suffix = ".oga"
    tmp_voice = NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_voice.write(response.content)

    tmp_voice_filename_ogg = tmp_voice.name
    tmp_voice_filename_wav = tmp_voice_filename_ogg[:-len(suffix)] + ".wav"

    subprocess.call(['ffmpeg', '-i', tmp_voice_filename_ogg, tmp_voice_filename_wav])

    converted_wav = open(tmp_voice_filename_wav, "rb")
    converted_wav_bin = converted_wav.read()

    tmp_voice.close()
    converted_wav.close()

    os.remove(tmp_voice_filename_ogg)
    os.remove(tmp_voice_filename_wav)

    return converted_wav_bin


def _send_binary_to_google_speech(content):
    """
    sends binary data of voice to google speech
    """
    config = {
        "language_code": LANG,
        "sample_rate_hertz": SAMPLE_RATE_HERTZ,
        "encoding": ENCODING_TYPE,
        "audio_channel_count": CHANNEL_COUNT,
        "enable_automatic_punctuation": ENABLE_AUTOMATIC_PUNCTUATION,
        "model": SPEECH_MODEL,
    }
    audio = {"content": content}
    speech_response = speech_client.recognize(config=config, audio=audio)
    return speech_response


def _check_google_speech_response(response):
    result = response.results[-1]
    logger.info("Google speech response results", result)
    any_alternatives = result.alternatives or []
    if len(any_alternatives) > 0:
        transcription = any_alternatives[0].transcript
        return transcription
    return None


def get_text_from_speech(file_id):
    """
    gets text from voice
    """
    try:
        file = _get_audio_file_data(file_id)
        content = _get_binary_content(file)
        response = _send_binary_to_google_speech(content)
        result = _check_google_speech_response(response)
        logger.info("Result of voice recognition", result)
        return result
    except (AttributeError, ValueError, RuntimeError) as ex:
        logger.error("Error during voice recognition", { "exception": ex, "file_id": file_id })
        return None
