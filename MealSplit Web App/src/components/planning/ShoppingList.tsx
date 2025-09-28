import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ShoppingCart, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { planningAPI } from '../../services/api';
import { ShoppingListItem } from '../../types';

interface ShoppingListProps {
  weekId: number;
}

export function ShoppingList({ weekId }: ShoppingListProps) {
  const queryClient = useQueryClient();

  const { data: items = [], isLoading, error } = useQuery({
    queryKey: ['shopping-list', weekId],
    queryFn: () => planningAPI.getShoppingList(weekId),
  });

  const markPurchasedMutation = useMutation({
    mutationFn: planningAPI.markItemPurchased,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shopping-list', weekId] });
    },
  });

  const handleTogglePurchased = (item: ShoppingListItem) => {
    if (!item.is_purchased) {
      markPurchasedMutation.mutate(item.id);
    }
  };

  const purchasedItems = items.filter(item => item.is_purchased);
  const remainingItems = items.filter(item => !item.is_purchased);
  const totalItems = items.length;
  const progressPercentage = totalItems > 0 ? (purchasedItems.length / totalItems) * 100 : 0;

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading shopping list...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load shopping list. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  if (items.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Shopping List
          </CardTitle>
          <CardDescription>
            No items in your shopping list yet. Add some recipes to generate a list!
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5" />
              Shopping List
            </CardTitle>
            <CardDescription>
              {purchasedItems.length} of {totalItems} items purchased
            </CardDescription>
          </div>
          <Badge variant={purchasedItems.length === totalItems ? "success" : "secondary"}>
            {Math.round(progressPercentage)}% Complete
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {markPurchasedMutation.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to update item. Please try again.
            </AlertDescription>
          </Alert>
        )}

        {/* Progress Bar */}
        <div className="w-full bg-muted rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        {/* Remaining Items */}
        {remainingItems.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
              To Buy ({remainingItems.length})
            </h4>
            {remainingItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors"
              >
                <Checkbox
                  checked={false}
                  onCheckedChange={() => handleTogglePurchased(item)}
                  disabled={markPurchasedMutation.isPending}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="font-medium truncate">
                      {item.ingredient.name}
                    </p>
                    <div className="flex items-center gap-2 ml-2">
                      <span className="text-sm text-muted-foreground whitespace-nowrap">
                        {item.total_quantity} {item.unit}
                      </span>
                      {item.ingredient.category && (
                        <Badge variant="outline" className="text-xs">
                          {item.ingredient.category}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Purchased Items */}
        {purchasedItems.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
              Purchased ({purchasedItems.length})
            </h4>
            {purchasedItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center space-x-3 p-3 border rounded-lg bg-muted/30 opacity-75"
              >
                <Checkbox checked={true} disabled />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="font-medium truncate line-through">
                      {item.ingredient.name}
                    </p>
                    <div className="flex items-center gap-2 ml-2">
                      <span className="text-sm text-muted-foreground whitespace-nowrap">
                        {item.total_quantity} {item.unit}
                      </span>
                      {item.ingredient.category && (
                        <Badge variant="outline" className="text-xs">
                          {item.ingredient.category}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                <Check className="h-4 w-4 text-green-600" />
              </div>
            ))}
          </div>
        )}

        {/* Summary */}
        {totalItems > 0 && (
          <div className="mt-4 p-3 bg-primary/5 border border-primary/20 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span>Shopping Progress</span>
              <span className="font-medium">
                {purchasedItems.length}/{totalItems} items completed
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}