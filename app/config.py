"""
Application configuration using Pydantic Settings.
Manages all configuration options with environment variable overrides.
"""

import os


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # App settings
        self.app_name = os.getenv("APP_NAME", "stock-market")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.env = os.getenv("ENV", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
        
        # SMTP settings
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", "")
        self.email_to = self._parse_list(os.getenv("EMAIL_TO", ""))
        
        # Gemini settings (placeholder)
        self.gemini_api_keys = self._parse_list(os.getenv("GEMINI_API_KEY", ""))
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # NSE settings (placeholder)
        self.nse_indices = self._parse_list(
            os.getenv("NSE_INDEX_NAMES", "NIFTY 100,NIFTY MIDCAP 100,NIFTY SMALLCAP 100")
        )
        self.near_52_week_low_pct = float(os.getenv("NEAR_52_WEEK_LOW_PCT", "5.0"))
        self.segment_top_n = int(os.getenv("SEGMENT_TOP_N", "20"))
        
        # Scheduler settings
        self.schedule_hour = int(os.getenv("SCHEDULE_HOUR", "4"))
        self.schedule_minute = int(os.getenv("SCHEDULE_MINUTE", "0"))
    
    def _parse_list(self, value: str) -> list[str]:
        """Parse comma-separated string into list."""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]


# Singleton settings instance
settings = Settings()
