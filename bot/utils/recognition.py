import json
from typing import Tuple, Union, Optional
import logging
import os
import subprocess
from tempfile import NamedTemporaryFile
import requests

from google.cloud import speech

TOKEN = os.environ["TOKEN"]

LANG = "ru-RU"
SAMPLE_RATE_HERTZ = 44100
ENCODING_TYPE = "LINEAR16"
CHANNEL_COUNT = 1
ENABLE_AUTOMATIC_PUNCTUATION = True
SPEECH_MODEL = "default"

OGA = ".oga"
MP4 = ".mp4"

VIDEO = "video"
AUDIO = "audio"

logger = logging.getLogger(__name__)


class Dummy:
    "dummy class to substitute speech client when in dev mode"

    def __getattribute__(self, name):
        def funcoff(*args, **kwargs):
            raise Exception(
                "google speech failed to initialize, voice recognition unavailable"
            )

        return funcoff


try:
    speech_client = speech.SpeechClient()
# pylint: disable=W0702
except:  # noqa
    logger.error("failed to initialize google speech")
    speech_client = Dummy()


def _get_tg_resource(file_id: str) -> Tuple[bytes, Union[AUDIO, str]]:
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url)
    json_response = response.json()
    logger.info("Data has been obtained: \n%s", json.dumps(json_response, indent=4))
    file_path = json_response["result"]["file_path"]
    url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    response = requests.get(url, stream=True)

    return (response.content, AUDIO) if OGA in file_path else (response.content, VIDEO)


def _get_converted_audio_content(buffer: bytes) -> Optional[bytes]:
    with NamedTemporaryFile(suffix=OGA) as tmp_voice:
        tmp_voice.write(buffer)

        tmp_voice_filename_ogg = tmp_voice.name
        tmp_voice_filename_wav = tmp_voice_filename_ogg[: -len(OGA)] + ".wav"

        try:
            subprocess.call(
                ["ffmpeg", "-i", tmp_voice_filename_ogg, tmp_voice_filename_wav]
            )
        except subprocess.CalledProcessError as err:
            logger.error("error with ffmpeg while processing %s: %s", OGA, err)
            return None

        with open(tmp_voice_filename_wav, "rb") as converted_wav:
            converted_wav_bin = converted_wav.read()

        os.remove(tmp_voice_filename_wav)

    return converted_wav_bin


def _send_binary_to_google_speech(content):
    """Sends binary data of voice to google speech."""
    config = {
        "language_code": LANG,
        "sample_rate_hertz": SAMPLE_RATE_HERTZ,
        "encoding": ENCODING_TYPE,
        "audio_channel_count": CHANNEL_COUNT,
        "enable_automatic_punctuation": ENABLE_AUTOMATIC_PUNCTUATION,
        "model": SPEECH_MODEL,
    }
    audio = {"content": content}
    # noinspection PyTypeChecker
    return speech_client.recognize(config=config, audio=audio)


def _check_google_speech_response(response) -> str:
    result = response.results[-1]
    logger.info("Google speech response results: %s", result)

    any_alternatives = result.alternatives or []
    if len(any_alternatives) == 0:
        return None

    transcription = any_alternatives[0].transcript
    return transcription


def _get_converted_video_content(buffer: bytes) -> Optional[bytes]:
    with NamedTemporaryFile(suffix=MP4) as tmp_video:
        tmp_video.write(buffer)

        tmp_video_filename_mp4 = tmp_video.name
        tmp_audio_filename_wav = tmp_video_filename_mp4[: -len(MP4)] + ".wav"

        try:
            subprocess.call(
                [
                    "ffmpeg",
                    "-i",
                    tmp_video_filename_mp4,
                    "-acodec",
                    "libvorbis",
                    tmp_audio_filename_wav,
                ]
            )
        except subprocess.CalledProcessError as err:
            logger.error("error with ffmpeg while processing %s: %s", MP4, err)
            return None

        with open(tmp_audio_filename_wav, "rb") as converted_wav:
            converted_wav_bin = converted_wav.read()

        os.remove(tmp_audio_filename_wav)

    return converted_wav_bin


def get_recognized_text(file_id: str):
    try:
        bin_data, file_type = _get_tg_resource(file_id)

        converted_content = (
            _get_converted_audio_content(bin_data)
            if file_type == AUDIO
            else _get_converted_video_content(bin_data)
        )
        if converted_content is None:
            return converted_content

        response = _send_binary_to_google_speech(converted_content)
        result = _check_google_speech_response(response)
        logger.info("Result of voice recognition: %s", result)
        return result
    except (AttributeError, ValueError, RuntimeError) as ex:
        logger.error(
            "Error during the voice recognition %s",
            {"exception": ex, "file_id": file_id},
        )
        return None


__all__ = ["get_recognized_text"]
