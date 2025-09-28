import { useQuery } from '@tanstack/react-query';
import { FileText, Clock, CheckCircle, XCircle, Eye, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { receiptsAPI } from '../../services/api';
import { Receipt } from '../../types';

interface ReceiptsListProps {
  onReceiptSelect?: (receipt: Receipt) => void;
  selectedReceiptId?: number;
}

export function ReceiptsList({ onReceiptSelect, selectedReceiptId }: ReceiptsListProps) {
  const { data: receipts = [], isLoading, error } = useQuery({
    queryKey: ['receipts'],
    queryFn: receiptsAPI.getAll,
    refetchInterval: 5000, // Poll for OCR updates
  });

  const getStatusIcon = (status: Receipt['ocr_status']) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusText = (status: Receipt['ocr_status']) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading receipts...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <XCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load receipts. Please try again.
        </AlertDescription>
      </Alert>
    );
  }

  if (receipts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Receipts</CardTitle>
          <CardDescription>
            Upload your first receipt to get started with MealSplit
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center py-8">
          <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">
            Your receipts will appear here after uploading
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Recent Receipts ({receipts.length})</h3>
      </div>

      <div className="space-y-3">
        {receipts.map((receipt) => (
          <Card 
            key={receipt.id}
            className={`cursor-pointer transition-colors hover:bg-muted/50 ${
              selectedReceiptId === receipt.id ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => onReceiptSelect?.(receipt)}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3 min-w-0 flex-1">
                  <div className="flex-shrink-0">
                    <FileText className="h-8 w-8 text-primary" />
                  </div>
                  
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <p className="font-medium truncate">
                        {receipt.store_name || receipt.filename}
                      </p>
                      <Badge 
                        variant="secondary" 
                        className="flex items-center space-x-1 text-xs"
                      >
                        {getStatusIcon(receipt.ocr_status)}
                        <span>{getStatusText(receipt.ocr_status)}</span>
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <span>{formatDate(receipt.upload_date)}</span>
                      <span>{formatCurrency(receipt.total_amount)}</span>
                      <span className="truncate">{receipt.filename}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-3">
                  {receipt.ocr_status === 'completed' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onReceiptSelect?.(receipt);
                      }}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Review
                    </Button>
                  )}
                </div>
              </div>

              {receipt.ocr_status === 'failed' && (
                <div className="mt-3 p-2 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive">
                  OCR processing failed. Please try uploading the receipt again.
                </div>
              )}

              {receipt.ocr_status === 'processing' && (
                <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-700">
                  Processing receipt text... This may take a few moments.
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}