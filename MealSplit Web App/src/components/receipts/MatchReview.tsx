import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form@7.55.0';
import { Search, Check, X, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { matchesAPI } from '../../services/api';
import { IngredientMatch, Ingredient, ConfirmMatchRequest } from '../../types';

interface MatchReviewProps {
  receiptId: number;
  weekId?: number;
  onAllMatched?: () => void;
}

interface MatchFormData {
  ingredient_id: number;
  quantity: number;
  unit: string;
}

export function MatchReview({ receiptId, weekId, onAllMatched }: MatchReviewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMatch, setSelectedMatch] = useState<IngredientMatch | null>(null);
  const queryClient = useQueryClient();

  const { data: matches = [], isLoading, error } = useQuery({
    queryKey: ['pending-matches', weekId || 0],
    queryFn: () => matchesAPI.getPending(weekId || 0),
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const { data: searchResults = [] } = useQuery({
    queryKey: ['ingredient-search', searchQuery],
    queryFn: () => matchesAPI.searchIngredients(searchQuery),
    enabled: searchQuery.length > 2,
  });

  const confirmMutation = useMutation({
    mutationFn: ({ lineId, data }: { lineId: number; data: ConfirmMatchRequest }) =>
      matchesAPI.confirm(lineId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-matches', receiptId] });
      setSelectedMatch(null);
      reset();
      
      // Check if all matches are complete
      const remainingMatches = matches.filter(m => m.id !== selectedMatch?.id);
      if (remainingMatches.length === 0) {
        onAllMatched?.();
      }
    },
  });

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<MatchFormData>();

  const watchedIngredientId = watch('ingredient_id');

  const handleMatchSelect = (match: IngredientMatch) => {
    setSelectedMatch(match);
    setValue('quantity', match.detected_quantity || 1);
    setValue('unit', match.ingredient?.typical_unit || 'piece');
    if (match.ingredient) {
      setValue('ingredient_id', match.ingredient.id);
    }
    setSearchQuery('');
  };

  const handleIngredientSelect = (ingredient: Ingredient) => {
    setValue('ingredient_id', ingredient.id);
    setValue('unit', ingredient.typical_unit || 'piece');
    setSearchQuery('');
  };

  const onSubmit = (data: MatchFormData) => {
    if (!selectedMatch) return;
    
    confirmMutation.mutate({
      lineId: selectedMatch.receipt_line_id,
      data,
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  if (isLoading) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading matches...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="max-w-4xl mx-auto">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load matches. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  if (matches.length === 0) {
    return (
      <Alert className="max-w-4xl mx-auto">
        <Check className="h-4 w-4" />
        <AlertDescription>
          All receipt items have been matched! You can now view the settlement.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Review and Confirm Matches</CardTitle>
          <CardDescription>
            Review the automatic ingredient matches and confirm or correct them
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pending Matches List */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Pending Matches ({matches.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {matches.map((match) => (
              <div
                key={match.id}
                className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedMatch?.id === match.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-muted-foreground'
                }`}
                onClick={() => handleMatchSelect(match)}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="font-medium text-sm">
                    {match.receipt_line.line_text}
                  </div>
                  <Badge 
                    variant="secondary" 
                    className={getConfidenceColor(match.confidence_score)}
                  >
                    {Math.round(match.confidence_score * 100)}%
                  </Badge>
                </div>
                
                {match.ingredient && (
                  <div className="text-sm text-muted-foreground">
                    Suggested: {match.ingredient.name}
                    {match.detected_quantity && (
                      <span> • {match.detected_quantity} {match.unit}</span>
                    )}
                    {match.detected_price && (
                      <span> • ${match.detected_price.toFixed(2)}</span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Match Confirmation Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              {selectedMatch ? 'Confirm Match' : 'Select a Match'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedMatch ? (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {confirmMutation.error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {confirmMutation.error instanceof Error 
                        ? confirmMutation.error.message 
                        : 'Failed to confirm match'}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Receipt Line Info */}
                <div className="p-3 bg-muted/50 rounded-lg">
                  <Label className="text-sm">Receipt Line</Label>
                  <p className="font-medium">{selectedMatch.receipt_line.line_text}</p>
                  {selectedMatch.receipt_line.detected_price && (
                    <p className="text-sm text-muted-foreground">
                      Price: ${selectedMatch.receipt_line.detected_price.toFixed(2)}
                    </p>
                  )}
                </div>

                {/* Ingredient Search */}
                <div className="space-y-2">
                  <Label htmlFor="ingredient-search">Search Ingredients</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="ingredient-search"
                      type="text"
                      placeholder="Type to search ingredients..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  
                  {/* Search Results */}
                  {searchResults.length > 0 && (
                    <div className="border rounded-lg max-h-40 overflow-y-auto">
                      {searchResults.map((ingredient) => (
                        <button
                          key={ingredient.id}
                          type="button"
                          className="w-full text-left p-2 hover:bg-muted/50 flex justify-between items-center"
                          onClick={() => handleIngredientSelect(ingredient)}
                        >
                          <span>{ingredient.name}</span>
                          {ingredient.category && (
                            <Badge variant="outline" className="text-xs">
                              {ingredient.category}
                            </Badge>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selected Ingredient */}
                {watchedIngredientId && (
                  <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg">
                    <Label className="text-sm">Selected Ingredient</Label>
                    <p className="font-medium">
                      {selectedMatch.ingredient?.name || 
                       searchResults.find(i => i.id === watchedIngredientId)?.name}
                    </p>
                  </div>
                )}

                <input
                  type="hidden"
                  {...register('ingredient_id', { required: 'Please select an ingredient' })}
                />
                {errors.ingredient_id && (
                  <p className="text-sm text-destructive">{errors.ingredient_id.message}</p>
                )}

                {/* Quantity */}
                <div className="space-y-2">
                  <Label htmlFor="quantity">Quantity</Label>
                  <Input
                    id="quantity"
                    type="number"
                    step="0.01"
                    {...register('quantity', {
                      required: 'Quantity is required',
                      min: { value: 0.01, message: 'Quantity must be positive' },
                    })}
                  />
                  {errors.quantity && (
                    <p className="text-sm text-destructive">{errors.quantity.message}</p>
                  )}
                </div>

                {/* Unit */}
                <div className="space-y-2">
                  <Label htmlFor="unit">Unit</Label>
                  <Input
                    id="unit"
                    type="text"
                    placeholder="e.g., piece, lb, kg, cup"
                    {...register('unit', { required: 'Unit is required' })}
                  />
                  {errors.unit && (
                    <p className="text-sm text-destructive">{errors.unit.message}</p>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button 
                    type="submit" 
                    disabled={confirmMutation.isPending || !watchedIngredientId}
                    className="flex-1"
                  >
                    {confirmMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Confirming...
                      </>
                    ) : (
                      <>
                        <Check className="h-4 w-4 mr-2" />
                        Confirm Match
                      </>
                    )}
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline"
                    onClick={() => setSelectedMatch(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </form>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Select a receipt line from the left to confirm or correct its ingredient match
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
