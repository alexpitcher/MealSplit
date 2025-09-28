import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DollarSign, Users, Calendar, ExternalLink, Loader2, AlertCircle, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import { settlementsAPI, splitwiseAPI } from '../../services/api';
import { WeekSettlementResponse } from '../../types';

interface SettlementSummaryProps {
  weekId: number;
}

export function SettlementSummary({ weekId }: SettlementSummaryProps) {
  const [isConnectingSplitwise, setIsConnectingSplitwise] = useState(false);
  const queryClient = useQueryClient();

  const { data: settlement, isLoading, error } = useQuery({
    queryKey: ['week-settlement', weekId],
    queryFn: () => settlementsAPI.getWeekSummary(weekId),
  });

  const closeWeekMutation = useMutation({
    mutationFn: () => settlementsAPI.closeWeek(weekId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['week-settlement', weekId] });
    },
  });

  const handleSplitwiseConnect = async () => {
    try {
      setIsConnectingSplitwise(true);
      const res = await fetch('http://localhost:8000/api/v1/splitwise/oauth/start', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
      });
      if (!res.ok) {
        throw new Error('Failed to start Splitwise OAuth');
      }
      const data = await res.json();
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        throw new Error('Authorization URL missing');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsConnectingSplitwise(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading settlement...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="max-w-4xl mx-auto">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load settlement data. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  if (!settlement) {
    return (
      <Alert className="max-w-4xl mx-auto">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          No settlement data found for this week.
        </AlertDescription>
      </Alert>
    );
  }

  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatDate = (dateString: string) => new Date(dateString).toLocaleDateString();

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Week Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Week Settlement
              </CardTitle>
              <CardDescription>
                Week starting {formatDate(settlement.week_plan.week_start)}
              </CardDescription>
            </div>
            <Badge 
              variant={settlement.week_plan.is_closed ? "default" : "secondary"}
              className="flex items-center gap-1"
            >
              {settlement.week_plan.is_closed ? (
                <>
                  <Check className="h-3 w-3" />
                  Closed
                </>
              ) : (
                'Active'
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <DollarSign className="h-8 w-8 mx-auto mb-2 text-primary" />
              <div className="text-2xl font-bold">{formatCurrency(settlement.total_spent)}</div>
              <p className="text-sm text-muted-foreground">Total Spent</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <Users className="h-8 w-8 mx-auto mb-2 text-primary" />
              <div className="text-2xl font-bold">{settlement.week_plan.participants.length}</div>
              <p className="text-sm text-muted-foreground">Participants</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <DollarSign className="h-8 w-8 mx-auto mb-2 text-primary" />
              <div className="text-2xl font-bold">{formatCurrency(settlement.per_person_share)}</div>
              <p className="text-sm text-muted-foreground">Per Person</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settlement Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Settlement Breakdown</CardTitle>
          <CardDescription>
            How much each person spent and owes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {settlement.settlements.map((userSettlement, index) => (
              <div key={userSettlement.id}>
                <div className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                      <span className="font-medium text-primary">
                        {userSettlement.participant.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium">{userSettlement.participant.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {userSettlement.participant.email}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right space-y-1">
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">
                        Spent: {formatCurrency(userSettlement.total_spent)}
                      </span>
                      <span className="text-muted-foreground">
                        Share: {formatCurrency(userSettlement.share_amount)}
                      </span>
                    </div>
                    <div className={`font-bold ${
                      userSettlement.net_amount > 0 
                        ? 'text-green-600' 
                        : userSettlement.net_amount < 0
                        ? 'text-red-600'
                        : 'text-muted-foreground'
                    }`}>
                      {userSettlement.net_amount > 0 
                        ? `Owed ${formatCurrency(userSettlement.net_amount)}`
                        : userSettlement.net_amount < 0
                        ? `Owes ${formatCurrency(Math.abs(userSettlement.net_amount))}`
                        : 'Even'
                      }
                    </div>
                  </div>
                </div>
                {index < settlement.settlements.length - 1 && <Separator />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Settlement Actions</CardTitle>
          <CardDescription>
            Manage this week's settlement
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {closeWeekMutation.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {closeWeekMutation.error instanceof Error 
                  ? closeWeekMutation.error.message 
                  : 'Failed to close week'}
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            {/* Splitwise Integration */}
            <Button
              onClick={handleSplitwiseConnect}
              disabled={isConnectingSplitwise}
              className="flex items-center gap-2"
            >
              {isConnectingSplitwise ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ExternalLink className="h-4 w-4" />
              )}
              Link Splitwise
            </Button>

            {/* Connect Splitwise (if not connected) */}
            <Button
              variant="outline"
              onClick={handleSplitwiseConnect}
              disabled={isConnectingSplitwise}
              className="flex items-center gap-2"
            >
              {isConnectingSplitwise ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ExternalLink className="h-4 w-4" />
              )}
              {isConnectingSplitwise ? 'Connecting...' : 'Connect Splitwise'}
            </Button>

            {/* Close Week */}
            {!settlement.week_plan.is_closed && (
              <Button
                variant="destructive"
                onClick={() => closeWeekMutation.mutate()}
                disabled={closeWeekMutation.isPending}
                className="flex items-center gap-2"
              >
                {closeWeekMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Close Week
              </Button>
            )}
          </div>

          <div className="text-sm text-muted-foreground space-y-1">
            <p>• Create Splitwise Expense: Automatically create an expense in Splitwise with the settlement amounts</p>
            <p>• Connect Splitwise: Link your Splitwise account for automatic expense creation</p>
            {!settlement.week_plan.is_closed && (
              <p>• Close Week: Finalize this week's settlement (cannot be undone)</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
