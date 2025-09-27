from sqlalchemy import Column, Integer, String, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    planning_week_id = Column(Integer, ForeignKey("planning_weeks.id"), primary_key=True)
    payer_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    payee_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    amount = Column(Float, nullable=False)

    # Relationships
    planning_week = relationship("PlanningWeek")
    payer = relationship("User", foreign_keys=[payer_id])
    payee = relationship("User", foreign_keys=[payee_id])


class SplitwiseLink(Base):
    __tablename__ = "splitwise_links"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    splitwise_user_id = Column(Integer, nullable=False)
    oauth_tokens = Column(JSON, nullable=False)  # Store access_token, refresh_token, etc.

    # Relationships
    user = relationship("User", back_populates="splitwise_link")