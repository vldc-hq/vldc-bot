"""
Warrant Canary skill - /chirp command

This skill implements a warrant canary feature where the bot responds
to /chirp with a PGP-signed "meow" message to prove authenticity.
"""

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Updater, CallbackContext

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

# GPG key configuration
GPG_KEY_DIR = Path("/app/.gnupg")
GPG_KEY_ID = None  # Will be set after key generation


def add_chirp(upd: Updater, handlers_group: int):
    """Register chirp command handler"""
    logger.info("registering chirp handlers")
    dp = upd.dispatcher
    dp.add_handler(ChatCommandHandler("chirp", chirp), handlers_group)


def _get_pgp_signature() -> str:
    """
    Get PGP signature for the meow message.

    Returns:
        PGP signature as a string, or empty string if signing fails
    """
    try:
        import gnupg  # pylint: disable=import-outside-toplevel

        # Initialize GPG
        gpg_home = str(GPG_KEY_DIR)
        gpg = gnupg.GPG(gnupghome=gpg_home)

        # Check if key exists
        keys = gpg.list_keys()
        if not keys:
            logger.warning("No GPG key found for signing")
            return ""

        # Sign the message
        message = "meow"
        signed_data = gpg.sign(message, keyid=keys[0]["keyid"], clearsign=True)

        if signed_data:
            return str(signed_data)

        # pylint: disable=no-member
        logger.error("Failed to sign message: %s", signed_data.stderr)
        return ""

    except ImportError:
        logger.warning("python-gnupg not installed, skipping signature")
        return ""
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error generating PGP signature: %s", e)
        return ""


def chirp(update: Update, context: CallbackContext):
    """
    Respond to /chirp command with a signed meow message.

    This is the warrant canary - if the bot doesn't respond or responds
    without a valid signature, something might be wrong.
    """
    chat_id = update.effective_chat.id

    # Get PGP signature
    signed_message = _get_pgp_signature()

    if signed_message:
        # Send signed message in a code block for better formatting
        response = f"```\n{signed_message}\n```"
        context.bot.send_message(chat_id, response, parse_mode="Markdown")
    else:
        # Fallback to unsigned message if signing fails
        context.bot.send_message(chat_id, "meow")

    logger.info("Chirp command executed for chat %s", chat_id)
