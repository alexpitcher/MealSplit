import { 
  AuthRequest, 
  AuthResponse, 
  UploadReceiptResponse, 
  ConfirmMatchRequest, 
  ConfirmMatchResponse,
  Receipt,
  IngredientMatch,
  Ingredient,
  WeekPlan,
  WeekSettlementResponse,
  ShoppingListItem,
  Recipe,
  ApiError,
  PaginatedResponse
} from '../types';

const API_BASE = 'http://localhost:8002/api/v1';

// Temporary default household selection until UI wiring is added
const DEFAULT_HOUSEHOLD_ID = 1;

class ApiClient {
  private getAuthToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getAuthToken();
    const url = `${API_BASE}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          message: `HTTP ${response.status}` 
        }));
        throw new Error(errorData.message || errorData.detail || `Request failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error occurred');
    }
  }

  // Auth endpoints
  async login(credentials: AuthRequest): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: credentials.email, password: credentials.password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    const tokens = await res.json();
    const meRes = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${tokens.access_token}` } });
    const me = await meRes.json();
    return { access_token: tokens.access_token, token_type: tokens.token_type, user: { id: me.id, email: me.email, name: me.display_name } } as AuthResponse;
  }

  async register(userData: AuthRequest & { name: string }): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userData.email, password: userData.password, display_name: userData.name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Signup failed');
    }
    const tokens = await res.json();
    const meRes = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${tokens.access_token}` } });
    const me = await meRes.json();
    return { access_token: tokens.access_token, token_type: tokens.token_type, user: { id: me.id, email: me.email, name: me.display_name } } as AuthResponse;
  }

  // Receipt endpoints
  async uploadReceipt(file: File): Promise<UploadReceiptResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('household_id', String(DEFAULT_HOUSEHOLD_ID));
    formData.append('store_name', '');
    formData.append('purchased_at', new Date().toISOString());

    const token = this.getAuthToken();
    const response = await fetch(`${API_BASE}/receipts/`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    const r = await response.json();
    const total = (r.receipt_lines || []).reduce((sum: number, l: any) => sum + (l.line_price || 0), 0);
    const mapped: Receipt = {
      id: r.id,
      filename: r.image_ref ? r.image_ref.split('/').pop() : `receipt_${r.id}`,
      upload_date: r.purchased_at,
      total_amount: total,
      store_name: r.store_name,
      ocr_status: r.status,
      user_id: r.payer_id,
    };
    return { receipt: mapped, message: 'Uploaded' } as UploadReceiptResponse;
  }

  async getReceipts(): Promise<Receipt[]> {
    // Map backend receipt list to frontend shape
    const data = await this.request<any[]>('/receipts/');
    return data.map((r) => ({
      id: r.id,
      filename: r.filename,
      upload_date: r.upload_date,
      total_amount: r.total_amount,
      store_name: r.store_name,
      ocr_status: r.ocr_status,
      user_id: r.user_id,
    })) as Receipt[];
  }

  async getReceipt(receiptId: number): Promise<Receipt> {
    const r = await this.request<any>(`/receipts/${receiptId}`);
    const total = (r.receipt_lines || []).reduce((sum: number, l: any) => sum + (l.line_price || 0), 0);
    return {
      id: r.id,
      filename: r.image_ref ? r.image_ref.split('/').pop() : `receipt_${r.id}`,
      upload_date: r.purchased_at,
      total_amount: total,
      store_name: r.store_name,
      ocr_status: r.status,
      user_id: r.payer_id,
    } as Receipt;
  }

  // Match endpoints
  async getPendingMatches(weekId: number): Promise<IngredientMatch[]> {
    // Backend returns suggested matches by week; not mapped to UI shape yet
    await this.request<any>(`/receipts/weeks/${weekId}/matches/pending`);
    return [];
  }

  async confirmMatch(
    lineId: number, 
    data: ConfirmMatchRequest
  ): Promise<ConfirmMatchResponse> {
    return this.request<ConfirmMatchResponse>(`/matches/${lineId}/confirm`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async searchIngredients(_query: string): Promise<Ingredient[]> {
    // Not available in backend yet
    return [];
  }

  // Week plan endpoints
  async getCurrentWeek(): Promise<WeekPlan> {
    return this.request<WeekPlan>('/weeks/current');
  }

  async getWeekSettlement(weekId: number): Promise<WeekSettlementResponse> {
    return this.request<WeekSettlementResponse>(`/settlements/weeks/${weekId}/settlement`);
  }

  async closeWeek(weekId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/settlements/weeks/${weekId}/close`, {
      method: 'POST',
    });
  }

  // Shopping list endpoints
  async getShoppingList(weekId: number): Promise<ShoppingListItem[]> {
    return this.request<ShoppingListItem[]>(`/weeks/${weekId}/shopping-list`);
  }

  async markItemPurchased(itemId: number): Promise<ShoppingListItem> {
    return this.request<ShoppingListItem>(`/shopping-list/${itemId}/purchased`, {
      method: 'POST',
    });
  }

  // Recipe endpoints
  async getRecipes(): Promise<Recipe[]> {
    return this.request<Recipe[]>('/recipes/');
  }

  async addRecipeToWeek(weekId: number, recipeId: number, servings: number): Promise<void> {
    return this.request(`/weeks/${weekId}/recipes`, {
      method: 'POST',
      body: JSON.stringify({
        recipe_id: recipeId,
        planned_servings: servings,
      }),
    });
  }

  // Splitwise integration
  async connectSplitwise(userId: number, accessToken: string): Promise<{ message: string }> {
    return this.request<{ message: string }>('/splitwise/connect', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        access_token: accessToken,
      }),
    });
  }

  async createSplitwiseExpense(weekId: number): Promise<{ message: string; expense_id: number }> {
    return this.request<{ message: string; expense_id: number }>(`/splitwise/weeks/${weekId}/expense`, {
      method: 'POST',
    });
  }
}

export const api = new ApiClient();

// Convenience exports for different API sections
export const authAPI = {
  login: api.login.bind(api),
  register: api.register.bind(api),
};

export const receiptsAPI = {
  upload: api.uploadReceipt.bind(api),
  getAll: api.getReceipts.bind(api),
  getById: api.getReceipt.bind(api),
};

export const matchesAPI = {
  getPending: api.getPendingMatches.bind(api),
  confirm: api.confirmMatch.bind(api),
  searchIngredients: api.searchIngredients.bind(api),
};

export const settlementsAPI = {
  getWeekSummary: api.getWeekSettlement.bind(api),
  closeWeek: api.closeWeek.bind(api),
};

export const planningAPI = {
  getCurrentWeek: api.getCurrentWeek.bind(api),
  getShoppingList: api.getShoppingList.bind(api),
  markItemPurchased: api.markItemPurchased.bind(api),
  getRecipes: api.getRecipes.bind(api),
  addRecipeToWeek: api.addRecipeToWeek.bind(api),
};

export const splitwiseAPI = {
  connect: api.connectSplitwise.bind(api),
  createExpense: api.createSplitwiseExpense.bind(api),
};
