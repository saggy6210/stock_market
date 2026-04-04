"""
Email Notifier.
Handles sending email notifications via SMTP.
"""

import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class EmailNotifier:
    """SMTP email notification handler."""
    
    def __init__(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_email: str = "",
        to_emails: list[str] = None,
    ):
        """
        Initialize the email notifier.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_emails: List of recipient email addresses
        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._from_email = from_email
        self._to_emails = to_emails or []
    
    def send(
        self,
        subject: str,
        body: str = "",
        html_body: str = None,
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject line
            body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self._is_configured():
            logger.warning(
                f"SMTP not configured - host={self._smtp_host}, "
                f"user={self._smtp_user}, from={self._from_email}, "
                f"to={self._to_emails}"
            )
            return False
        
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = ", ".join(self._to_emails)
            msg.set_content(body)
            
            if html_body:
                msg.add_alternative(html_body, subtype="html")
            
            logger.info(f"Connecting to SMTP server {self._smtp_host}:{self._smtp_port}")
            with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection failed (firewall/network?): {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {type(e).__name__}: {e}")
            return False
    
    def _is_configured(self) -> bool:
        """
        Check if SMTP is properly configured.
        
        Returns:
            bool: True if configured, False otherwise
        """
        return all([
            self._smtp_host,
            self._smtp_user,
            self._smtp_password,
            self._from_email,
            self._to_emails,
        ])
