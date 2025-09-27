from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    members = relationship("HouseholdUser", back_populates="household")
    planning_weeks = relationship("PlanningWeek", back_populates="household")
    receipts = relationship("Receipt", back_populates="household")


class HouseholdUser(Base):
    __tablename__ = "household_users"

    household_id = Column(Integer, ForeignKey("households.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    share_default = Column(Float, nullable=False, default=1.0)

    # Relationships
    household = relationship("Household", back_populates="members")
    user = relationship("User", back_populates="household_memberships")