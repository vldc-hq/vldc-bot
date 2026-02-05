import json
from typing import Tuple, Optional, Literal, Any, Callable, NoReturn
import logging
import os
import subprocess
from tempfile import NamedTemporaryFile
import requests
from requests.exceptions import RequestException

TOKEN = os.environ["TOKEN"]

LANG = "ru-RU"
SAMPLE_RATE_HERTZ = 48000
ENCODING_TYPE = "LINEAR16"
CHANNEL_COUNT = 1
ENABLE_AUTOMATIC_PUNCTUATION = True
SPEECH_MODEL = "default"

OGA = ".oga"
MP4 = ".mp4"

VIDEO: MediaType = "video"
MediaType = Literal["audio", "video"]

AUDIO: MediaType = "audio"

logger = logging.getLogger(__name__)

try:
    from google.cloud import speech
except Exception as exc:  # pylint: disable=broad-except
    speech = None
    logger.warning("google speech unavailable: %s", exc)


class Dummy:
    "dummy class to substitute speech client when in dev mode"

    def __getattribute__(self, name: str) -> Callable[..., NoReturn]:
        def funcoff(*args: Any, **kwargs: Any) -> NoReturn:
            raise Exception(
                "google speech failed to initialize, voice recognition unavailable"
            )

        return funcoff


credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
if speech is None:
    logger.info("google speech disabled: library is not available")
    speech_client: Any = Dummy()
elif not credentials_path or not os.path.exists(credentials_path):
    logger.info(
        "google speech disabled: GOOGLE_APPLICATION_CREDENTIALS is not set or file missing"
    )
    speech_client = Dummy()
else:
    try:
        speech_client = speech.SpeechClient()
    # pylint: disable=W0702
    except:  # noqa
        logger.error("failed to initialize google speech")
        speech_client = Dummy()


def _get_tg_resource(file_id: str) -> Optional[Tuple[bytes, MediaType]]:
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        json_response = response.json()
        logger.info("Data has been obtained: \n%s", json.dumps(json_response, indent=4))
        file_path = json_response["result"]["file_path"]
    except (RequestException, KeyError, ValueError) as exc:
        logger.error("failed to fetch tg file metadata: %s", exc)
        return None

    try:
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
    except RequestException as exc:
        logger.error("failed to download tg file: %s", exc)
        return None

    return (response.content, AUDIO) if OGA in file_path else (response.content, VIDEO)


def _get_converted_audio_content(buffer: bytes) -> Optional[bytes]:
    with NamedTemporaryFile(suffix=OGA) as tmp_voice:
        tmp_voice.write(buffer)

        tmp_voice_filename_ogg = tmp_voice.name
        tmp_voice_filename_wav = tmp_voice_filename_ogg[: -len(OGA)] + ".wav"

        try:
            result = subprocess.run(
                ["ffmpeg", "-i", tmp_voice_filename_ogg, tmp_voice_filename_wav],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as err:
            logger.error("error with ffmpeg while processing %s: %s", OGA, err)
            return None

        if result.returncode != 0 or not os.path.exists(tmp_voice_filename_wav):
            logger.error("ffmpeg failed to produce wav for %s", OGA)
            return None

        with open(tmp_voice_filename_wav, "rb") as converted_wav:
            converted_wav_bin = converted_wav.read()

        os.remove(tmp_voice_filename_wav)

    return converted_wav_bin


def _send_binary_to_google_speech(content: bytes) -> Any:
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


def _check_google_speech_response(response: Any) -> Optional[str]:
    results = list(getattr(response, "results", []) or [])
    if not results:
        return None
    result = results[-1]
    logger.info("Google speech response results: %s", result)

    any_alternatives = list(getattr(result, "alternatives", []) or [])
    if not any_alternatives:
        return None

    transcription = getattr(any_alternatives[0], "transcript", None)
    if transcription is None:
        return None
    return str(transcription)


def _get_converted_video_content(buffer: bytes) -> Optional[bytes]:
    with NamedTemporaryFile(suffix=MP4) as tmp_video:
        tmp_video.write(buffer)

        tmp_video_filename_mp4 = tmp_video.name
        tmp_audio_filename_wav = tmp_video_filename_mp4[: -len(MP4)] + ".wav"

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    tmp_video_filename_mp4,
                    "-acodec",
                    "libvorbis",
                    tmp_audio_filename_wav,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as err:
            logger.error("error with ffmpeg while processing %s: %s", MP4, err)
            return None

        if result.returncode != 0 or not os.path.exists(tmp_audio_filename_wav):
            logger.error("ffmpeg failed to produce wav for %s", MP4)
            return None

        with open(tmp_audio_filename_wav, "rb") as converted_wav:
            converted_wav_bin = converted_wav.read()

        os.remove(tmp_audio_filename_wav)

    return converted_wav_bin


def get_recognized_text(file_id: str):
    try:
        tg_resource = _get_tg_resource(file_id)
        if tg_resource is None:
            return None
        bin_data, file_type = tg_resource

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
