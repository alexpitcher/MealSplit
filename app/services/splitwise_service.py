import logging
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.settlement import SplitwiseLink, Settlement

logger = logging.getLogger(__name__)


class SplitwiseService:
    """Service for integrating with Splitwise API."""

    def __init__(self):
        self.base_url = "https://secure.splitwise.com/api/v3.0"
        self.client_id = settings.SPLITWISE_CLIENT_ID
        self.client_secret = settings.SPLITWISE_CLIENT_SECRET

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        if not self.client_id or not self.client_secret:
            raise ValueError("Splitwise credentials not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://secure.splitwise.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.SPLITWISE_REDIRECT_URI,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )

            if response.status_code != 200:
                logger.error(f"Failed to exchange code for tokens: {response.text}")
                raise Exception("Failed to exchange authorization code")

            return response.json()

    async def get_current_user(self, access_token: str) -> Dict[str, Any]:
        """Get current user information from Splitwise."""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/get_current_user",
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Failed to get current user: {response.text}")
                raise Exception("Failed to get user information")

            data = response.json()
            return data.get("user", {})

    async def create_expense(
        self,
        access_token: str,
        description: str,
        cost: float,
        currency: str,
        users: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create an expense in Splitwise."""
        headers = {"Authorization": f"Bearer {access_token}"}

        expense_data = {
            "description": description,
            "cost": str(cost),
            "currency_code": currency,
            "users": users
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/create_expense",
                headers=headers,
                json=expense_data
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create expense: {response.text}")
                raise Exception("Failed to create expense")

            return response.json()

    async def sync_settlements_to_splitwise(
        self,
        db: Session,
        planning_week_id: int,
        household_users: List[User]
    ) -> bool:
        """Sync week settlements to Splitwise."""
        try:
            # Get settlements for the week
            settlements = db.query(Settlement).filter(
                Settlement.planning_week_id == planning_week_id
            ).all()

            if not settlements:
                logger.info(f"No settlements to sync for week {planning_week_id}")
                return True

            # Group settlements by payer
            expenses_by_payer = {}
            for settlement in settlements:
                payer_id = settlement.payer_id
                if payer_id not in expenses_by_payer:
                    expenses_by_payer[payer_id] = []
                expenses_by_payer[payer_id].append(settlement)

            # Create Splitwise expenses for each payer
            for payer_id, payer_settlements in expenses_by_payer.items():
                payer = next((u for u in household_users if u.id == payer_id), None)
                if not payer:
                    continue

                # Get payer's Splitwise link
                splitwise_link = db.query(SplitwiseLink).filter(
                    SplitwiseLink.user_id == payer_id
                ).first()

                if not splitwise_link:
                    logger.warning(f"No Splitwise link for user {payer_id}")
                    continue

                # Calculate total amount and prepare user shares
                total_amount = sum(s.amount for s in payer_settlements)
                splitwise_users = self._prepare_splitwise_users(
                    household_users, payer_settlements
                )

                # Create expense in Splitwise
                expense_description = f"MealSplit - Week {planning_week_id}"
                tokens = splitwise_link.oauth_tokens

                await self.create_expense(
                    access_token=tokens.get("access_token"),
                    description=expense_description,
                    cost=total_amount,
                    currency="USD",
                    users=splitwise_users
                )

                logger.info(
                    f"Synced ${total_amount} expense to Splitwise for user {payer_id}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to sync settlements to Splitwise: {e}")
            return False

    def _prepare_splitwise_users(
        self,
        household_users: List[User],
        settlements: List[Settlement]
    ) -> List[Dict[str, Any]]:
        """Prepare user data for Splitwise expense creation."""
        users = []

        # Create user entry for each person involved in settlements
        user_amounts = {}
        for settlement in settlements:
            # Payer paid the amount
            if settlement.payer_id not in user_amounts:
                user_amounts[settlement.payer_id] = {"paid": 0, "owed": 0}
            user_amounts[settlement.payer_id]["paid"] += settlement.amount

            # Payee owes the amount
            if settlement.payee_id not in user_amounts:
                user_amounts[settlement.payee_id] = {"paid": 0, "owed": 0}
            user_amounts[settlement.payee_id]["owed"] += settlement.amount

        # Convert to Splitwise format
        for user_id, amounts in user_amounts.items():
            user = next((u for u in household_users if u.id == user_id), None)
            if user and user.splitwise_link:
                users.append({
                    "user_id": user.splitwise_link.splitwise_user_id,
                    "paid_share": str(amounts["paid"]),
                    "owed_share": str(amounts["owed"])
                })

        return users