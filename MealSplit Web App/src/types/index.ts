// Core entity types
export interface User {
  id: number;
  email: string;
  name: string;
  splitwise_user_id?: number;
}

export interface Receipt {
  id: number;
  filename: string;
  upload_date: string;
  total_amount: number;
  store_name?: string;
  ocr_status: 'pending' | 'processing' | 'completed' | 'failed';
  ocr_text?: string;
  user_id: number;
}

export interface ReceiptLine {
  id: number;
  receipt_id: number;
  line_text: string;
  detected_price?: number;
  detected_quantity?: number;
  confidence_score?: number;
}

export interface Ingredient {
  id: number;
  name: string;
  category?: string;
  typical_unit?: string;
}

export interface IngredientMatch {
  id: number;
  receipt_line_id: number;
  ingredient_id: number;
  quantity: number;
  unit: string;
  confidence_score: number;
  is_confirmed: boolean;
  ingredient: Ingredient;
  receipt_line: ReceiptLine;
}

export interface Recipe {
  id: number;
  name: string;
  description?: string;
  servings: number;
  created_by: number;
}

export interface RecipeIngredient {
  id: number;
  recipe_id: number;
  ingredient_id: number;
  quantity: number;
  unit: string;
  ingredient: Ingredient;
}

export interface WeekPlan {
  id: number;
  week_start: string;
  is_closed: boolean;
  participants: User[];
}

export interface WeekPlanRecipe {
  id: number;
  week_plan_id: number;
  recipe_id: number;
  planned_servings: number;
  recipe: Recipe;
}

export interface ShoppingListItem {
  id: number;
  week_plan_id: number;
  ingredient_id: number;
  total_quantity: number;
  unit: string;
  is_purchased: boolean;
  ingredient: Ingredient;
}

export interface Settlement {
  id: number;
  week_plan_id: number;
  participant_id: number;
  total_spent: number;
  share_amount: number;
  net_amount: number;
  participant: User;
}

export interface SplitwiseExpense {
  id: number;
  settlement_id: number;
  splitwise_expense_id: number;
  amount: number;
}

// API request/response types
export interface UploadReceiptRequest {
  file: File;
}

export interface UploadReceiptResponse {
  receipt: Receipt;
  message: string;
}

export interface ConfirmMatchRequest {
  ingredient_id: number;
  quantity: number;
  unit: string;
}

export interface ConfirmMatchResponse {
  match: IngredientMatch;
  message: string;
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface WeekSettlementResponse {
  week_plan: WeekPlan;
  settlements: Settlement[];
  total_spent: number;
  per_person_share: number;
}

// UI state types
export interface ApiError {
  message: string;
  detail?: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}