import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { integrationsApi } from '../api/integrations';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export function GitHubCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
    const [errorMessage, setErrorMessage] = useState<string>('');
    const hasProcessed = useRef(false);

    useEffect(() => {
        const handleCallback = async () => {
            // Prevent double-execution (React StrictMode)
            if (hasProcessed.current) return;
            hasProcessed.current = true;

            // Check for error from GitHub
            const error = searchParams.get('error');
            if (error) {
                setStatus('error');
                setErrorMessage(error === 'access_denied'
                    ? 'GitHub authorization was cancelled.'
                    : `GitHub authorization error: ${error}`);
                setTimeout(() => {
                    navigate('/integrations');
                }, 3000);
                return;
            }

            // Extract code and state from URL
            const code = searchParams.get('code');
            const state = searchParams.get('state');

            if (!code) {
                setStatus('error');
                setErrorMessage('No authorization code received from GitHub.');
                setTimeout(() => {
                    navigate('/integrations');
                }, 3000);
                return;
            }

            try {
                // Exchange code for token via backend
                const response = await integrationsApi.handleCallback(code, state || undefined);

                if (response.status === 'connected') {
                    setStatus('success');
                    // Invalidate integrations query to refresh the list
                    queryClient.invalidateQueries({ queryKey: ['integrations'] });

                    // Get the redirect path from localStorage (saved before OAuth redirect)
                    const redirectPath = localStorage.getItem('github_oauth_redirect') || '/integrations';
                    console.log('GitHub Callback Success. Redirecting to:', redirectPath);
                    localStorage.removeItem('github_oauth_redirect');

                    // Redirect after a brief success message
                    setTimeout(() => {
                        console.log('Executing navigation to:', redirectPath);
                        navigate(redirectPath);
                    }, 2000);
                } else {
                    throw new Error('Connection failed');
                }
            } catch (error: any) {
                console.error('GitHub callback error:', error);

                // If it's a 401/Bad Credentials but we already processed (race condition?), 
                // we might want to handle it gracefully, but strict-mode fix should prevent it entirely.

                setStatus('error');
                setErrorMessage(
                    error?.response?.data?.error ||
                    error?.response?.data?.detail ||
                    error?.message ||
                    'Failed to connect GitHub. Please try again.'
                );
                setTimeout(() => {
                    navigate('/integrations');
                }, 3000);
            }
        };

        handleCallback();
    }, [searchParams, navigate, queryClient]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
            <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
                {status === 'processing' && (
                    <>
                        <Loader2 className="h-12 w-12 animate-spin text-indigo-600 mx-auto mb-4" />
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                            Connecting GitHub...
                        </h2>
                        <p className="text-gray-500 dark:text-gray-400">
                            Please wait while we complete the connection.
                        </p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                            GitHub Connected Successfully!
                        </h2>
                        <p className="text-gray-500 dark:text-gray-400">
                            Redirecting you back...
                        </p>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <XCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                            Connection Failed
                        </h2>
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
                            <p className="text-sm text-red-700 dark:text-red-300 flex items-center justify-center">
                                <AlertCircle className="h-4 w-4 mr-2" />
                                {errorMessage}
                            </p>
                        </div>
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                            Redirecting you back to integrations...
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
