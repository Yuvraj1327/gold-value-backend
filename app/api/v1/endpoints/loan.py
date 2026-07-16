import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_loan_service
from app.core.rate_limit import limiter
from app.core.security import CurrentUser, get_current_user
from app.schemas.loan import LoanEstimateRequest, LoanEstimateResponse
from app.services.loan_service import LoanService

router = APIRouter(prefix="/loan", tags=["Loan Estimator"])


@router.post("/estimate", response_model=LoanEstimateResponse)
@limiter.limit("30/minute")
async def estimate_loan(
    request: Request,
    payload: LoanEstimateRequest,
    user: CurrentUser = Depends(get_current_user),
    service: LoanService = Depends(get_loan_service),
) -> LoanEstimateResponse:
    """Gold Loan Estimator (SOP requirement #4): loan eligibility (LTV),
    monthly EMI, and full repayment summary — stateless, based on either a
    raw `gold_value` or a saved `calculation_id`.
    """
    return await service.estimate(uuid.UUID(user.id), payload)
