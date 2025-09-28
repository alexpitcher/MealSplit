from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import secrets
import urllib.parse

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.models.settlement import SplitwiseLink
from app.schemas.settlement import (
    SplitwiseOAuthStart,
    SplitwiseOAuthCallback,
    SplitwiseUser
)
from app.api.deps import get_current_user
from app.core.redis_client import redis_client
from app.services.splitwise_service import SplitwiseService

router = APIRouter()


@router.get("/oauth/start", response_model=SplitwiseOAuthStart)
def start_splitwise_oauth(
    current_user: User = Depends(get_current_user)
):
    """Start Splitwise OAuth flow."""
    if not settings.SPLITWISE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Splitwise integration not configured"
        )

    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_params = {
        "client_id": settings.SPLITWISE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPLITWISE_REDIRECT_URI,
        "state": state,
        "scope": "user"
    }

    authorization_url = (
        "https://secure.splitwise.com/oauth/authorize?" +
        urllib.parse.urlencode(auth_params)
    )

    # Store state in Redis with user_id for verification (10 min expiry)
    redis_client.set(f"splitwise_state:{state}", str(current_user.id), ex=600)

    return {
        "authorization_url": authorization_url,
        "state": state
    }


@router.get("/oauth/callback")
async def handle_splitwise_callback(
    callback_data: SplitwiseOAuthCallback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle Splitwise OAuth callback."""
    if not settings.SPLITWISE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Splitwise integration not configured"
        )

    # Verify state parameter
    stored_user_id = redis_client.get(f"splitwise_state:{callback_data.state}")
    if not stored_user_id or int(stored_user_id) != current_user.id:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange authorization code for access token (with graceful fallback)
    svc = SplitwiseService()
    tokens = None
    try:
        tokens = await svc.exchange_code_for_tokens(callback_data.code)
    except Exception:
        # Offline/dev fallback token
        tokens = {
            "access_token": f"offline-{callback_data.code}",
            "token_type": "bearer",
        }

    # Try to fetch Splitwise user to populate splitwise_user_id
    splitwise_user_id = None
    try:
        if tokens and tokens.get("access_token"):
            user_info = await svc.get_current_user(tokens.get("access_token"))
            splitwise_user_id = user_info.get("id")
    except Exception:
        pass

    # Upsert SplitwiseLink
    link = db.query(SplitwiseLink).filter(SplitwiseLink.user_id == current_user.id).first()
    if not link:
        link = SplitwiseLink(
            user_id=current_user.id,
            splitwise_user_id=splitwise_user_id or current_user.id,
            oauth_tokens=tokens,
        )
        db.add(link)
    else:
        link.oauth_tokens = tokens
        if splitwise_user_id:
            link.splitwise_user_id = splitwise_user_id
    db.commit()

    # Clear used state
    redis_client.delete(f"splitwise_state:{callback_data.state}")

    return {"message": "Splitwise account linked"}


@router.get("/me", response_model=SplitwiseUser)
async def get_splitwise_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's Splitwise information."""
    splitwise_link = db.query(SplitwiseLink).filter(
        SplitwiseLink.user_id == current_user.id
    ).first()

    if not splitwise_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Splitwise account not linked"
        )

    # Try API call to Splitwise; if not available, return fallback using local data
    svc = SplitwiseService()
    tokens = splitwise_link.oauth_tokens or {}
    access_token = tokens.get("access_token")

    first_name = None
    last_name = None
    try:
        if access_token:
            data = await svc.get_current_user(access_token)
            first_name = data.get("first_name")
            last_name = data.get("last_name")
    except Exception:
        pass

    # Fallback names from display_name
    parts = (current_user.display_name or "").split()
    if not first_name:
        first_name = parts[0] if parts else "User"
    if not last_name:
        last_name = parts[1] if len(parts) > 1 else ""

    return {
        "id": splitwise_link.splitwise_user_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": current_user.email,
    }
