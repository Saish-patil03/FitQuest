import os
import sys
import smtplib
import logging
from typing import Optional
from email.message import EmailMessage
from backend.config import settings

logger = logging.getLogger("fitquest.email")

class EmailService:
    """
    Dedicated Email Delivery Service for FitQuest AI.
    Supports real Gmail/SMTP email delivery with STARTTLS authentication,
    rich HTML + plain-text fallback templating, safe error handling,
    masked recipient logging, and development mode stdout printing.
    """

    @staticmethod
    def mask_email(email: str) -> str:
        """
        Masks an email address for privacy in logs (e.g. nihar@example.com -> n***@example.com).
        """
        if not email or "@" not in email:
            return "***"
        user, domain = email.split("@", 1)
        if len(user) <= 1:
            masked_user = "*"
        else:
            masked_user = user[0] + "***"
        return f"{masked_user}@{domain}"

    def send_password_reset_email(self, to_email: str, reset_url: str) -> bool:
        """
        Dispatches a password reset email to `to_email` with the specified `reset_url`.
        Returns True on successful delivery or development log print, and False on failure.
        """
        if not to_email or not reset_url:
            logger.warning("[EMAIL WARNING] Cannot send reset email: Missing recipient email or reset URL.")
            return False

        # Read provider from settings / env
        provider = os.environ.get("EMAIL_PROVIDER", settings.EMAIL_PROVIDER).strip().lower()

        # DEVELOPMENT FALLBACK MODE
        if provider in ("development", "dev", ""):
            dev_msg = f"\n[DEV] Password reset link:\n{reset_url}\n"
            print(dev_msg, flush=True)
            sys.stdout.flush()
            logger.info(f"[DEV] Printed password reset link for {self.mask_email(to_email)}")
            return True

        # REAL SMTP DELIVERY MODE
        if provider in ("smtp", "gmail"):
            smtp_host = os.environ.get("SMTP_HOST", settings.SMTP_HOST)
            smtp_port = int(os.environ.get("SMTP_PORT", str(settings.SMTP_PORT)))
            smtp_username = os.environ.get("SMTP_USERNAME", settings.SMTP_USERNAME or "")
            smtp_password = os.environ.get("SMTP_PASSWORD", settings.SMTP_PASSWORD or "")
            email_from = os.environ.get("EMAIL_FROM", settings.EMAIL_FROM or smtp_username)

            masked_recipient = self.mask_email(to_email)

            if not smtp_username or not smtp_password:
                config_err = (
                    f"\n[EMAIL CONFIG ERROR] EMAIL_PROVIDER is set to '{provider}', but SMTP_USERNAME or SMTP_PASSWORD "
                    f"is not configured in your .env file.\n"
                    f"-> Please enter your Gmail address and 16-character App Password in .env,\n"
                    f"-> OR set EMAIL_PROVIDER=development in .env to use terminal reset links.\n"
                )
                print(config_err, flush=True)
                sys.stdout.flush()
                logger.error(f"[EMAIL CONFIG ERROR] Missing SMTP credentials when sending reset email to {masked_recipient}")
                return False


            try:
                msg = EmailMessage()
                msg["Subject"] = "FitQuest AI — Reset Your Password"
                msg["From"] = email_from
                msg["To"] = to_email

                # Plain Text Alternative
                text_content = (
                    "FitQuest AI — Reset Your Password\n\n"
                    "We received a request to reset your FitQuest AI password.\n\n"
                    f"Click the link below to set a new password:\n{reset_url}\n\n"
                    "This link expires in 20 minutes.\n\n"
                    "If you did not request a password reset, you can safely ignore this email.\n\n"
                    "— FitQuest AI Team"
                )
                msg.set_content(text_content)

                # HTML Email Template
                html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FitQuest AI — Reset Your Password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: 'Outfit', 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #f1f5f9;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0b0f19; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" max-width="560px" cellspacing="0" cellpadding="0" style="background-color: #151c2e; border: 1px solid rgba(0, 242, 254, 0.2); border-radius: 16px; padding: 36px 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          
          <!-- Logo Header -->
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <span style="font-size: 28px; font-weight: 800; color: #00f2fe; letter-spacing: 1px;">
                ⚡ FITQUEST <span style="color: #4facfe;">AI</span>
              </span>
            </td>
          </tr>

          <!-- Main Title -->
          <tr>
            <td align="center" style="padding-bottom: 16px;">
              <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #ffffff;">Reset Your Password</h1>
            </td>
          </tr>

          <!-- Body Description -->
          <tr>
            <td align="left" style="padding-bottom: 28px; font-size: 15px; line-height: 1.6; color: #94a3b8;">
              Hello,<br><br>
              We received a request to reset the password for your <strong>FitQuest AI</strong> account. Click the button below to set a new password:
            </td>
          </tr>

          <!-- CTA Button -->
          <tr>
            <td align="center" style="padding-bottom: 32px;">
              <a href="{reset_url}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); color: #0b0f19; font-weight: 700; font-size: 15px; padding: 14px 32px; text-decoration: none; border-radius: 30px; box-shadow: 0 4px 15px rgba(0, 242, 254, 0.4);">
                RESET PASSWORD
              </a>
            </td>
          </tr>

          <!-- Expiration Notice & Fallback Link -->
          <tr>
            <td align="left" style="padding-bottom: 24px; font-size: 13px; line-height: 1.5; color: #64748b; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 20px;">
              <strong style="color: #ff7e5f;">⏱️ Note:</strong> This password reset link expires in <strong>20 minutes</strong>.<br><br>
              If the button above does not work, copy and paste this link into your browser:<br>
              <a href="{reset_url}" style="color: #00f2fe; word-break: break-all;">{reset_url}</a>
            </td>
          </tr>

          <!-- Disclaimer Footer -->
          <tr>
            <td align="center" style="font-size: 12px; color: #475569; line-height: 1.4;">
              If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.<br><br>
              © FitQuest AI Assistant. All rights reserved.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
                msg.add_alternative(html_content, subtype="html")

                # Connect via SMTP & STARTTLS
                with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.send_message(msg)

                logger.info(f"[EMAIL] Password reset email sent successfully to {masked_recipient}")
                print(f"[EMAIL] Password reset email sent successfully to {masked_recipient}", flush=True)
                return True

            except Exception as err:
                logger.error(f"[EMAIL ERROR] Failed to send password reset email to {masked_recipient}: {err}")
                return False

        logger.warning(f"[EMAIL WARNING] Unknown EMAIL_PROVIDER '{provider}'. Defaulting to development stdout print.")
        dev_msg = f"\n[DEV] Password reset link:\n{reset_url}\n"
        print(dev_msg, flush=True)
        return True

email_service = EmailService()
