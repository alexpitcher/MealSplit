from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date


class RecipeIngredientBase(BaseModel):
    name: str
    qty: float
    unit: str
    tags: Optional[Dict[str, Any]] = None


class RecipeIngredientCreate(RecipeIngredientBase):
    pass


class RecipeIngredient(RecipeIngredientBase):
    id: int
    recipe_id: int

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    mealie_id: Optional[str] = None
    title: str
    base_servings: int
    meta: Optional[Dict[str, Any]] = None


class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientCreate] = []


class Recipe(RecipeBase):
    id: int
    ingredients: List[RecipeIngredient] = []

    class Config:
        from_attributes = True


class WeekRecipeBase(BaseModel):
    recipe_id: int
    planned_servings: int


class WeekRecipeCreate(WeekRecipeBase):
    pass


class WeekRecipe(WeekRecipeBase):
    id: int
    planning_week_id: int
    recipe: Optional[Recipe] = None

    class Config:
        from_attributes = True


class PlanningWeekBase(BaseModel):
    household_id: int
    week_start: date


class PlanningWeekCreate(PlanningWeekBase):
    pass


class PlanningWeek(PlanningWeekBase):
    id: int
    created_at: datetime
    week_recipes: List[WeekRecipe] = []

    class Config:
        from_attributes = True


class ShoppingItemBase(BaseModel):
    canonical_name: str
    qty_needed: float
    unit: str


class ShoppingItem(ShoppingItemBase):
    id: int
    planning_week_id: int

    class Config:
        from_attributes = True


class ShoppingList(BaseModel):
    planning_week_id: int
    items: List[ShoppingItem]