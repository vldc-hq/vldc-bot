from unittest import TestCase
from unittest.mock import Mock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import CallbackContext

from skills.towel_mode import catch_reply


class TowelModeTestCase(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = 12345
        self.chat_id = 67890
        self.bot_id = 11111

        # Mock user in quarantine
        self.mock_user = {"_id": self.user_id, "rel_messages": []}

        # Mock Update
        self.update = Mock(spec=Update)
        self.update.effective_user = Mock(spec=User)
        self.update.effective_user.id = self.user_id
        self.update.effective_user.name = "TestUser"

        self.update.effective_chat = Mock(spec=Chat)
        self.update.effective_chat.id = self.chat_id

        self.update.effective_message = Mock(spec=Message)
        self.update.effective_message.message_id = 999
        self.update.effective_message.reply_to_message = Mock(spec=Message)
        self.update.effective_message.reply_to_message.from_user = Mock(spec=User)
        self.update.effective_message.reply_to_message.from_user.id = self.bot_id

        self.update.message = self.update.effective_message

        # Mock CallbackContext
        self.context = Mock(spec=CallbackContext)
        self.context.bot = Mock()
        self.context.bot.get_me = Mock(return_value=Mock(id=self.bot_id))
        self.context.bot.delete_message = Mock()
        self.context.bot.send_message = Mock(return_value=Mock(message_id=888))

    @patch("skills.towel_mode.db")
    def test_short_reply_less_than_10_chars(self, mock_db):
        """Test that replies with less than 10 characters are rejected with feedback"""
        # Setup
        mock_db.find_user.return_value = self.mock_user
        mock_db.add_user_rel_message = Mock()
        self.update.effective_message.text = "Too short"  # 9 characters

        # Execute
        catch_reply(self.update, self.context)

        # Verify message was deleted
        self.context.bot.delete_message.assert_called_once_with(self.chat_id, 999)

        # Verify feedback message was sent
        self.context.bot.send_message.assert_called_once()
        call_args = self.context.bot.send_message.call_args
        self.assertEqual(call_args[0][0], self.chat_id)
        self.assertIn("слишком короткий", call_args[0][1])

        # Verify feedback message was added to rel_messages
        mock_db.add_user_rel_message.assert_called_once_with(self.user_id, 888)

        # Verify user was NOT removed from quarantine
        mock_db.delete_user.assert_not_called()

    @patch("skills.towel_mode.db")
    def test_empty_reply(self, mock_db):
        """Test that empty replies are rejected with feedback"""
        # Setup
        mock_db.find_user.return_value = self.mock_user
        mock_db.add_user_rel_message = Mock()
        self.update.effective_message.text = ""

        # Execute
        catch_reply(self.update, self.context)

        # Verify message was deleted
        self.context.bot.delete_message.assert_called_once_with(self.chat_id, 999)

        # Verify feedback message was sent
        self.context.bot.send_message.assert_called_once()

        # Verify user was NOT removed from quarantine
        mock_db.delete_user.assert_not_called()

    @patch("skills.towel_mode.db")
    def test_none_text_reply(self, mock_db):
        """Test that None text is handled as empty string"""
        # Setup
        mock_db.find_user.return_value = self.mock_user
        mock_db.add_user_rel_message = Mock()
        self.update.effective_message.text = None

        # Execute
        catch_reply(self.update, self.context)

        # Verify message was deleted
        self.context.bot.delete_message.assert_called_once_with(self.chat_id, 999)

        # Verify feedback message was sent
        self.context.bot.send_message.assert_called_once()

    @patch("skills.towel_mode.is_worthy")
    @patch("skills.towel_mode.db")
    def test_valid_reply_10_chars_or_more(self, mock_db, mock_is_worthy):
        """Test that replies with 10+ characters that pass is_worthy check are accepted"""
        # Setup
        mock_db.find_user.return_value = self.mock_user
        mock_db.delete_user = Mock()
        mock_is_worthy.return_value = True
        self.update.effective_message.text = "Valid reply with enough characters"

        # Execute
        catch_reply(self.update, self.context)

        # Verify is_worthy was called
        mock_is_worthy.assert_called_once_with("Valid reply with enough characters")

        # Verify user was removed from quarantine
        mock_db.delete_user.assert_called_once_with(user_id=self.user_id)

        # Verify welcome message was sent
        self.update.message.reply_text.assert_called_once_with(
            "Добро пожаловать в VLDC!"
        )

    @patch("skills.towel_mode.is_worthy")
    @patch("skills.towel_mode.db")
    def test_invalid_reply_10_chars_or_more(self, mock_db, mock_is_worthy):
        """Test that replies with 10+ characters that fail is_worthy check are deleted"""
        # Setup
        mock_db.find_user.return_value = self.mock_user
        mock_is_worthy.return_value = False
        self.update.effective_message.text = "Spam message here"

        # Execute
        catch_reply(self.update, self.context)

        # Verify is_worthy was called
        mock_is_worthy.assert_called_once_with("Spam message here")

        # Verify message was deleted (with timeout parameter)
        self.context.bot.delete_message.assert_called_once_with(self.chat_id, 999, 10)

        # Verify user was NOT removed from quarantine
        mock_db.delete_user.assert_not_called()

    @patch("skills.towel_mode.db")
    def test_non_quarantine_user(self, mock_db):
        """Test that messages from non-quarantine users are ignored"""
        # Setup
        mock_db.find_user.return_value = None
        self.update.effective_message.text = "Some message"

        # Execute
        catch_reply(self.update, self.context)

        # Verify nothing happened
        self.context.bot.delete_message.assert_not_called()
        self.context.bot.send_message.assert_not_called()
        mock_db.delete_user.assert_not_called()
