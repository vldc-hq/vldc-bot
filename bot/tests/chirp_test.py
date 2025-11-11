"""
Tests for the chirp (warrant canary) skill.
"""

from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# We need to mock telegram modules before importing skills
sys.modules["telegram"] = MagicMock()
sys.modules["telegram.ext"] = MagicMock()
sys.modules["telegram.error"] = MagicMock()

from skills.chirp import chirp, _get_pgp_signature


class ChirpTestCase(TestCase):
    """Test cases for the chirp warrant canary skill."""

    def test_chirp_basic_response(self):
        """Test that chirp responds with a message."""
        # Mock the Update and CallbackContext
        update = Mock()
        context = Mock()
        update.effective_chat.id = 12345
        context.bot.send_message = Mock()

        # Mock _get_pgp_signature to return empty (no signature)
        with patch("skills.chirp._get_pgp_signature", return_value=""):
            chirp(update, context)

            # Verify send_message was called with "meow"
            context.bot.send_message.assert_called_once()
            args = context.bot.send_message.call_args
            self.assertEqual(args[0][0], 12345)  # chat_id
            self.assertEqual(args[0][1], "meow")  # message

    def test_chirp_with_signature(self):
        """Test that chirp responds with a signed message."""
        update = Mock()
        context = Mock()
        update.effective_chat.id = 12345
        context.bot.send_message = Mock()

        # Mock _get_pgp_signature to return a signed message
        signed_msg = (
            "-----BEGIN PGP SIGNED MESSAGE-----\nmeow\n-----END PGP SIGNATURE-----"
        )
        with patch("skills.chirp._get_pgp_signature", return_value=signed_msg):
            chirp(update, context)

            # Verify send_message was called with the signed message in markdown
            context.bot.send_message.assert_called_once()
            args = context.bot.send_message.call_args
            self.assertEqual(args[0][0], 12345)  # chat_id
            self.assertIn(signed_msg, args[0][1])  # message contains signature
            self.assertEqual(args[1]["parse_mode"], "Markdown")

    def test_get_pgp_signature_no_gnupg(self):
        """Test _get_pgp_signature when gnupg is not available."""
        with patch("skills.chirp.gnupg", None):
            # Should return empty string if gnupg import fails
            signature = _get_pgp_signature()
            self.assertEqual(signature, "")

    def test_get_pgp_signature_no_keys(self):
        """Test _get_pgp_signature when no GPG keys are available."""
        mock_gpg = Mock()
        mock_gpg.list_keys.return_value = []

        with patch("skills.chirp.gnupg.GPG", return_value=mock_gpg):
            signature = _get_pgp_signature()
            self.assertEqual(signature, "")

    def test_get_pgp_signature_success(self):
        """Test _get_pgp_signature when signing succeeds."""
        mock_gpg = Mock()
        mock_gpg.list_keys.return_value = [{"keyid": "test123"}]

        # Create a mock signed data object
        mock_signed = MagicMock()
        mock_signed.__str__ = Mock(return_value="SIGNED MESSAGE")
        mock_signed.__bool__ = Mock(return_value=True)
        mock_gpg.sign.return_value = mock_signed

        with patch("skills.chirp.gnupg.GPG", return_value=mock_gpg):
            signature = _get_pgp_signature()
            self.assertEqual(signature, "SIGNED MESSAGE")
            mock_gpg.sign.assert_called_once_with(
                "meow", keyid="test123", clearsign=True
            )
