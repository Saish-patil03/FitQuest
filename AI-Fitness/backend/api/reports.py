from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.report import (
    ReportAvailabilityResponse,
    FitQuestReportResponse,
)
from backend.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["User Progress Reports"])


@router.get("/available", response_model=ReportAvailabilityResponse, summary="Get Report Availability For User")
def get_report_availability(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns available and locked reporting periods (15, 30, 60, 90 days) for the authenticated athlete.
    """
    try:
        return report_service.get_report_availability(db=db, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check report availability: {e}")


@router.get("/{period_days}", response_model=FitQuestReportResponse, summary="Generate Structured Progress Report")
def get_progress_report(
    period_days: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generates and returns structured progress report data for the specified time period.
    Enforces user isolation and historical duration availability.
    """
    if period_days not in report_service.ALLOWED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reporting period '{period_days}'. Minimum period is 15 days. Allowed periods: {report_service.ALLOWED_PERIODS}"
        )
    try:
        return report_service.generate_progress_report(db=db, user_id=user_id, period_days=period_days)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate progress report: {e}")


@router.get("/{period_days}/pdf", summary="Download Progress Report as PDF")
def download_progress_report_pdf(
    period_days: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Renders and streams a high-resolution, branded PDF progress report for the authenticated athlete.
    """
    if period_days not in report_service.ALLOWED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reporting period '{period_days}'. Allowed periods: {report_service.ALLOWED_PERIODS}"
        )
    try:
        report_data = report_service.generate_progress_report(db=db, user_id=user_id, period_days=period_days)
        pdf_bytes = report_service.render_pdf(report_data)
        filename = f"fitquest_{period_days}day_progress_report.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to render progress report PDF: {e}")
