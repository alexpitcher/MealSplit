from typing import List, Dict
from pydantic import BaseModel


class SettlementBase(BaseModel):
    planning_week_id: int
    payer_id: int
    payee_id: int
    amount: float


class SettlementCreate(SettlementBase):
    pass


class Settlement(SettlementBase):

    class Config:
        from_attributes = True


class WeekSettlement(BaseModel):
    planning_week_id: int
    settlements: List[Settlement]
    total_amount: float
    is_balanced: bool


class SplitwiseLinkBase(BaseModel):
    splitwise_user_id: int


class SplitwiseLink(SplitwiseLinkBase):
    user_id: int

    class Config:
        from_attributes = True


class SplitwiseUser(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class SplitwiseOAuthStart(BaseModel):
    authorization_url: str
    state: str


class SplitwiseOAuthCallback(BaseModel):
    code: str
    state: str