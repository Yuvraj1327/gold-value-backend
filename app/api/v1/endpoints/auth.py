from fastapi import APIRouter, Depends, Request

from app.api.deps import get_auth_service
from app.core.rate_limit import limiter
from app.schemas.auth import AuthResponse, LoginRequest, LogoutRequest, SignupRequest
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=201)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    payload: SignupRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    """Creates a new Supabase-authenticated user (email/password).

    Google sign-in and anonymous guest sessions are initiated directly from
    the Flutter app via the Supabase SDK (they involve a native OAuth/guest
    flow the backend doesn't mediate) and simply arrive here already
    authenticated on subsequent requests.
    """
    return await auth_service.signup(payload)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await auth_service.login(payload)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    payload: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await auth_service.logout(payload.access_token)
    return MessageResponse(message="Signed out successfully.")
