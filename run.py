"""
Entry point for the stock market application.
Starts the uvicorn server with configuration-based settings.
"""

import uvicorn

from app.config import settings


def main():
    """Main entry point."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    main()
