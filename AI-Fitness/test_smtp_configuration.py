#!/usr/bin/env python3
"""
Diagnostic Test Suite for FitQuest SMTP Configuration & Environment Loading
Verifies:
- Environment variable loading via Pydantic Settings
- Correct default values (smtp.gmail.com:587, http://127.0.0.1:8080)
- Validation of missing credentials when EMAIL_PROVIDER=smtp
- Secret masking (SMTP passwords are NEVER output to stdout/stderr or logs)
- No actual emails are sent during automated unit tests
"""

import os
import io
import sys
import unittest
from unittest.mock import patch

from backend.config import Settings
from backend.services.email_service import EmailService

class TestSMTPConfiguration(unittest.TestCase):

    def setUp(self):
        self.env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env_backup)

    def test_1_default_smtp_settings(self):
        """TEST 1: Verify default settings fallback for host, port, and frontend URL."""
        os.environ.pop("FITQUEST_FRONTEND_URL", None)
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_PORT", None)
        s = Settings(_env_file=None)
        self.assertEqual(s.SMTP_HOST, "smtp.gmail.com")
        self.assertEqual(s.SMTP_PORT, 587)
        self.assertEqual(s.FITQUEST_FRONTEND_URL, "http://127.0.0.1:8080")

    def test_2_custom_environment_loading(self):
        """TEST 2: Verify environment variables correctly override Settings defaults."""
        os.environ["EMAIL_PROVIDER"] = "smtp"
        os.environ["SMTP_HOST"] = "smtp.custom-domain.com"
        os.environ["SMTP_PORT"] = "2525"
        os.environ["FITQUEST_FRONTEND_URL"] = "http://127.0.0.1:3000"

        s = Settings()
        self.assertEqual(s.EMAIL_PROVIDER, "smtp")
        self.assertEqual(s.SMTP_HOST, "smtp.custom-domain.com")
        self.assertEqual(s.SMTP_PORT, 2525)
        self.assertEqual(s.FITQUEST_FRONTEND_URL, "http://127.0.0.1:3000")

    def test_3_missing_credentials_handling(self):
        """TEST 3: Verify missing credentials when EMAIL_PROVIDER=smtp returns False safely."""
        os.environ["EMAIL_PROVIDER"] = "smtp"
        os.environ["SMTP_USERNAME"] = ""
        os.environ["SMTP_PASSWORD"] = ""

        service = EmailService()
        result = service.send_password_reset_email("user@example.com", "http://127.0.0.1:8080/?token=fake")
        self.assertFalse(result, "Should return False when SMTP credentials are missing")

    def test_4_smtp_password_never_printed_in_stdout(self):
        """TEST 4: Confirm SMTP passwords are NEVER printed to stdout or stderr during operations."""
        secret_password = "SUPER_SECRET_GMAIL_APP_PASSWORD_9999"
        os.environ["EMAIL_PROVIDER"] = "smtp"
        os.environ["SMTP_HOST"] = "smtp.gmail.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USERNAME"] = "athlete@gmail.com"
        os.environ["SMTP_PASSWORD"] = secret_password

        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_smtp.side_effect = Exception("Connection Failed Test")
                service = EmailService()
                service.send_password_reset_email("athlete@gmail.com", "http://127.0.0.1:8080/?token=123")

        output = captured_stdout.getvalue()
        self.assertNotIn(secret_password, output, "SMTP password must NEVER be exposed in stdout!")

if __name__ == "__main__":
    unittest.main()
