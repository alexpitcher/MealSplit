import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner@2.0.3';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { Navigation } from './components/common/Navigation';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import { ReceiptUpload } from './components/receipts/ReceiptUpload';
import { ReceiptsList } from './components/receipts/ReceiptsList';
import { MatchReview } from './components/receipts/MatchReview';
import { SettlementSummary } from './components/settlements/SettlementSummary';
import { ShoppingList } from './components/planning/ShoppingList';
import { Receipt } from './types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

type ViewType = 'receipts' | 'settlements' | 'planning';

function AuthenticatedApp() {
  const [currentView, setCurrentView] = useState<ViewType>('receipts');
  const [selectedReceipt, setSelectedReceipt] = useState<Receipt | null>(null);
  const [showMatchReview, setShowMatchReview] = useState(false);
  const [currentWeekId] = useState(1);

  const handleReceiptUploadSuccess = (receipt: Receipt) => {
    setSelectedReceipt(receipt);
    // Matching disabled in initial integration
    setShowMatchReview(false);
  };

  const handleReceiptSelect = (receipt: Receipt) => {
    setSelectedReceipt(receipt);
    // Matching disabled in initial integration
    setShowMatchReview(false);
  };

  const handleBackToReceipts = () => {
    setShowMatchReview(false);
    setSelectedReceipt(null);
  };

  const handleMatchingComplete = () => {
    setShowMatchReview(false);
    setCurrentView('settlements');
  };

  const renderReceiptsView = () => {
    if (showMatchReview && selectedReceipt) {
      return (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">Review Matches</h2>
              <p className="text-muted-foreground">
                Receipt: {selectedReceipt.store_name || selectedReceipt.filename}
              </p>
            </div>
            <button
              onClick={handleBackToReceipts}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to receipts
            </button>
          </div>
          <MatchReview 
            receiptId={selectedReceipt.id}
            weekId={currentWeekId}
            onAllMatched={handleMatchingComplete}
          />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Receipts</h2>
          <p className="text-muted-foreground">
            Upload and review your meal receipts
          </p>
        </div>
        
        <ReceiptUpload onUploadSuccess={handleReceiptUploadSuccess} />
        <ReceiptsList 
          onReceiptSelect={handleReceiptSelect}
          selectedReceiptId={selectedReceipt?.id}
        />
      </div>
    );
  };

  const renderSettlementsView = () => {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Settlements</h2>
          <p className="text-muted-foreground">
            Review and settle weekly meal expenses
          </p>
        </div>
        
        <SettlementSummary weekId={currentWeekId} />
      </div>
    );
  };

  const renderPlanningView = () => {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Meal Planning</h2>
          <p className="text-muted-foreground">
            Plan your meals and manage your shopping list
          </p>
        </div>
        
        <ShoppingList weekId={currentWeekId} />
      </div>
    );
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'receipts':
        return renderReceiptsView();
      case 'settlements':
        return renderSettlementsView();
      case 'planning':
        return renderPlanningView();
      default:
        return renderReceiptsView();
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navigation 
        currentView={currentView} 
        onViewChange={setCurrentView} 
      />
      
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 pb-20 md:pb-6">
        {renderCurrentView()}
      </main>
    </div>
  );
}

function AuthWrapper() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
        <div className="w-full max-w-md">
          {authMode === 'login' ? (
            <LoginForm onToggleMode={() => setAuthMode('register')} />
          ) : (
            <RegisterForm onToggleMode={() => setAuthMode('login')} />
          )}
        </div>
      </div>
    );
  }

  return <AuthenticatedApp />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthWrapper />
        <Toaster position="top-right" />
      </AuthProvider>
    </QueryClientProvider>
  );
}
