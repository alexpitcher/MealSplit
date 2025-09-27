from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlanningWeek(Base):
    __tablename__ = "planning_weeks"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    household = relationship("Household", back_populates="planning_weeks")
    week_recipes = relationship("WeekRecipe", back_populates="planning_week")
    shopping_items = relationship("ShoppingItem", back_populates="planning_week")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    mealie_id = Column(String, unique=True, index=True)
    title = Column(String, nullable=False)
    base_servings = Column(Integer, nullable=False)
    meta = Column(JSON)

    # Relationships
    week_recipes = relationship("WeekRecipe", back_populates="recipe")
    ingredients = relationship("RecipeIngredient", back_populates="recipe")


class WeekRecipe(Base):
    __tablename__ = "week_recipes"

    id = Column(Integer, primary_key=True, index=True)
    planning_week_id = Column(Integer, ForeignKey("planning_weeks.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    planned_servings = Column(Integer, nullable=False)

    # Relationships
    planning_week = relationship("PlanningWeek", back_populates="week_recipes")
    recipe = relationship("Recipe", back_populates="week_recipes")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    name = Column(String, nullable=False)
    qty = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    tags = Column(JSON)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")
    shopping_item_links = relationship("ShoppingItemLink", back_populates="recipe_ingredient")
    line_matches = relationship("LineMatch", back_populates="recipe_ingredient")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, index=True)
    planning_week_id = Column(Integer, ForeignKey("planning_weeks.id"), nullable=False)
    canonical_name = Column(String, nullable=False)
    qty_needed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)

    # Relationships
    planning_week = relationship("PlanningWeek", back_populates="shopping_items")
    shopping_item_links = relationship("ShoppingItemLink", back_populates="shopping_item")


class ShoppingItemLink(Base):
    __tablename__ = "shopping_item_links"

    shopping_item_id = Column(Integer, ForeignKey("shopping_items.id"), primary_key=True)
    recipe_ingredient_id = Column(Integer, ForeignKey("recipe_ingredients.id"), primary_key=True)
    ratio = Column(Float, nullable=False)

    # Relationships
    shopping_item = relationship("ShoppingItem", back_populates="shopping_item_links")
    recipe_ingredient = relationship("RecipeIngredient", back_populates="shopping_item_links")