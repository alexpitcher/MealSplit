from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.user import User


class HouseholdBase(BaseModel):
    name: str


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdUpdate(BaseModel):
    name: Optional[str] = None


class HouseholdUserBase(BaseModel):
    user_id: int
    share_default: float = 1.0


class HouseholdUserCreate(HouseholdUserBase):
    pass


class HouseholdUserUpdate(BaseModel):
    share_default: Optional[float] = None


class HouseholdUser(HouseholdUserBase):
    household_id: int
    user: Optional[User] = None

    class Config:
        from_attributes = True


class Household(HouseholdBase):
    id: int
    created_at: datetime
    members: List[HouseholdUser] = []

    class Config:
        from_attributes = True


class HouseholdJoinRequest(BaseModel):
    household_id: int