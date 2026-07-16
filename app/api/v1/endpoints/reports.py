import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.api.deps import get_pdf_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.services.pdf_service import PdfService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/calculations/{calculation_id}/pdf")
@limiter.limit("20/minute")
async def download_calculation_pdf(
    request: Request,
    calculation_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    service: PdfService = Depends(get_pdf_service),
) -> Response:
    """Downloads a professional one-page PDF report for a saved
    calculation (SOP §8). Returns 404/403 via the same ownership check
    used everywhere else in the History feature — a user can only ever
    generate a report for their own calculation.
    """
    pdf_bytes = await service.generate_calculation_report(uuid.UUID(user.id), calculation_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="gold-value-{calculation_id}.pdf"',
        },
    )
