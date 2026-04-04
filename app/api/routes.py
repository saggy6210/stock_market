"""
API Routes.
Defines the REST API endpoints for the stock market service.
"""

from fastapi import APIRouter

from app.config import settings
from app.notification.emailer import EmailNotifier

router = APIRouter()


@router.get("/health")
def health():
    """
    Health check endpoint.
    
    Returns:
        dict: Status response {"status": "ok"}
    """
    return {"status": "ok"}


@router.get("/test-email")
def test_email():
    """
    Send a test email to verify SMTP configuration.
    
    Returns:
        dict: Result with success status
    """
    notifier = EmailNotifier(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        from_email=settings.email_from,
        to_emails=settings.email_to,
    )
    
    success = notifier.send(
        subject="Stock Market App - Test Email",
        body="This is a test email from the Stock Market application.",
    )
    
    return {
        "success": success,
        "message": "Test email sent" if success else "Failed to send email"
    }


@router.get("/stocks")
def get_stocks():
    """
    Get cached filtered stocks from last pipeline run.
    
    Returns:
        list: List of filtered stocks
    """
    # TODO: Implement get stocks
    return {"message": "Not implemented yet", "stocks": []}


@router.get("/run")
def run_pipeline():
    """
    Manually trigger the full pipeline.
    
    Returns:
        PipelineRunResult: Results of the pipeline run
    """
    # TODO: Implement run pipeline
    return {"message": "Not implemented yet"}
