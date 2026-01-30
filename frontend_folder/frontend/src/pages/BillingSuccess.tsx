import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useQueryClient } from '@tanstack/react-query';

export function BillingSuccess() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const sessionId = searchParams.get('session_id');
    const queryClient = useQueryClient();

    useEffect(() => {
        // Invalidate organization and me queries to ensure we fetch fresh subscription status
        queryClient.invalidateQueries({ queryKey: ['me'] });
        queryClient.invalidateQueries({ queryKey: ['organization'] });
    }, [queryClient]);

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
            <div className="bg-green-100 dark:bg-green-900/30 p-4 rounded-full mb-6">
                <CheckCircle className="h-16 w-16 text-green-600 dark:text-green-400" />
            </div>

            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                Payment Successful!
            </h1>

            <p className="text-gray-600 dark:text-gray-300 max-w-md mb-8">
                Thank you for upgrading to Pro! Your subscription is now active, and you have access to all premium features.
            </p>

            {sessionId && (
                <p className="text-xs text-gray-400 mb-8 font-mono">
                    Session ID: {sessionId.slice(0, 16)}...
                </p>
            )}

            <div className="space-x-4">
                <Button onClick={() => navigate('/dashboard')}>
                    Go to Dashboard
                </Button>
                <Button variant="outline" onClick={() => navigate('/settings/billing')}>
                    View Billing Settings
                </Button>
            </div>
        </div>
    );
}
