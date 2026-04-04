"""
WhatsApp Notifier.
Handles sending WhatsApp notifications via Twilio.
"""

# TODO: Implement WhatsAppNotifier class with:
# - send(message) - Sends WhatsApp message
# - Stub implementation (Twilio SDK not integrated)


class WhatsAppNotifier:
    """WhatsApp notification handler via Twilio."""
    
    def __init__(
        self,
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "",
        to_numbers: list[str] = None,
    ):
        """
        Initialize the WhatsApp notifier.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: WhatsApp sender number
            to_numbers: List of recipient WhatsApp numbers
        """
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._to_numbers = to_numbers or []
    
    def send(self, message: str) -> bool:
        """
        Send a WhatsApp notification.
        
        Args:
            message: Message text to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        # TODO: Implement WhatsApp sending via Twilio
        # Note: Twilio SDK integration not yet implemented
        pass
    
    def _is_configured(self) -> bool:
        """
        Check if Twilio is properly configured.
        
        Returns:
            bool: True if configured, False otherwise
        """
        # TODO: Implement configuration check
        pass
