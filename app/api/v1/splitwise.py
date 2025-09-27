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

    # TODO: Store state in Redis with user_id for verification
    # redis_client.set(f"splitwise_state:{state}", current_user.id, ex=600)

    return {
        "authorization_url": authorization_url,
        "state": state
    }


@router.get("/oauth/callback")
def handle_splitwise_callback(
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

    # TODO: Verify state parameter
    # stored_user_id = redis_client.get(f"splitwise_state:{callback_data.state}")
    # if not stored_user_id or int(stored_user_id) != current_user.id:
    #     raise HTTPException(status_code=400, detail="Invalid state parameter")

    # TODO: Exchange authorization code for access token
    # This would involve making a POST request to Splitwise token endpoint

    # For now, just return success
    return {"message": "Splitwise OAuth callback handled successfully"}


@router.get("/me", response_model=SplitwiseUser)
def get_splitwise_user(
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

    # TODO: Make API call to Splitwise to get user info
    # For now, return placeholder data
    return {
        "id": splitwise_link.splitwise_user_id,
        "first_name": "John",
        "last_name": "Doe",
        "email": current_user.email
    }