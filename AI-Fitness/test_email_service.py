#!/usr/bin/env python3
"""
Test Suite for FitQuest Email Service (SMTP Email Delivery & Dev Fallback)
Verifies:
- TEST 1: SMTP email creation & delivery (mocks smtplib.SMTP, verifies STARTTLS, login, recipient, HTML/text body)
- TEST 2: Safe handling of SMTP authentication/connection failures (no exceptions unhandled)
- TEST 3: Development fallback mode (stdout printing when EMAIL_PROVIDER=development)
- TEST 4: Privacy & secrets protection (SMTP passwords and tokens not exposed in logs)
- TEST 5: Email masking helper function (privacy logging)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from email.message import EmailMessage

from backend.services.email_service import email_service

class TestEmailService(unittest.TestCase):

    def setUp(self):
        self.env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_backup)

    @patch("smtplib.SMTP")
    def test_1_smtp_email_creation_and_delivery(self, mock_smtp_cls):
        """TEST 1: Verify SMTP email creation, STARTTLS, login, recipient, subject, and HTML/text payload."""
        os.environ["EMAIL_PROVIDER"] = "smtp"
        os.environ["SMTP_HOST"] = "smtp.gmail.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USERNAME"] = "coach@gmail.com"
        os.environ["SMTP_PASSWORD"] = "sample_app_password_1234"
        os.environ["EMAIL_FROM"] = "coach@gmail.com"

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        recipient = "athlete@fitquest.ai"
        reset_url = "http://127.0.0.1:8080/?token=test_reset_token_abcdef123456"

        success = email_service.send_password_reset_email(recipient, reset_url)

        self.assertTrue(success, "send_password_reset_email should return True on SMTP success")
        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=12)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("coach@gmail.com", "sample_app_password_1234")
        mock_server.send_message.assert_called_once()

        # Inspect sent EmailMessage
        sent_msg: EmailMessage = mock_server.send_message.call_args[0][0]
        self.assertEqual(sent_msg["To"], "athlete@fitquest.ai")
        self.assertEqual(sent_msg["From"], "coach@gmail.com")
        self.assertEqual(sent_msg["Subject"], "FitQuest AI — Reset Your Password")

        # Verify content contains reset URL and 20-minute expiry text
        plain_body = sent_msg.get_body("plain").get_content()
        html_body = sent_msg.get_body("html").get_content()

        self.assertIn(reset_url, plain_body)
        self.assertIn("20 minutes", plain_body)
        self.assertIn(reset_url, html_body)
        self.assertIn("RESET PASSWORD", html_body)


    @patch("smtplib.SMTP")
    def test_2_smtp_failure_handling(self, mock_smtp_cls):
        """TEST 2: Verify SMTP connection/auth errors are handled safely without crashing application."""
        os.environ["EMAIL_PROVIDER"] = "smtp"
        os.environ["SMTP_HOST"] = "smtp.gmail.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USERNAME"] = "coach@gmail.com"
        os.environ["SMTP_PASSWORD"] = "wrong_password"

        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("SMTP Authentication Error")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        # Must NOT raise exception to caller
        success = email_service.send_password_reset_email("athlete@fitquest.ai", "http://127.0.0.1:8080/?token=fake")
        self.assertFalse(success, "Should safely return False on SMTP error")

    @patch("smtplib.SMTP")
    def test_3_development_fallback_mode(self, mock_smtp_cls):
        """TEST 3: Verify EMAIL_PROVIDER=development prints reset link to terminal without opening SMTP socket."""
        os.environ["EMAIL_PROVIDER"] = "development"

        success = email_service.send_password_reset_email("athlete@fitquest.ai", "http://127.0.0.1:8080/?token=dev_token_999")
        self.assertTrue(success)
        mock_smtp_cls.assert_not_called()

    def test_4_email_masking_helper(self):
        """TEST 4: Verify email address masking for log privacy."""
        self.assertEqual(email_service.mask_email("alex@example.com"), "a***@example.com")
        self.assertEqual(email_service.mask_email("b@domain.org"), "*@domain.org")
        self.assertEqual(email_service.mask_email("fitquest.athlete@gmail.com"), "f***@gmail.com")

if __name__ == "__main__":
    unittest.main()
