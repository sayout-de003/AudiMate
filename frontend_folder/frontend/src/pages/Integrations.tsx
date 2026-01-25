import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { integrationsApi } from '../api/integrations';
import { Button } from '../components/ui/Button';
import { Loader2, Github, Cloud, CheckCircle, XCircle, Trash2, Plus } from 'lucide-react';

export function Integrations() {
    const queryClient = useQueryClient();


    const { data: integrations = [], isLoading } = useQuery({
        queryKey: ['integrations'],
        queryFn: integrationsApi.list
    });

    const connectGitHubMutation = useMutation({
        mutationFn: integrationsApi.connectGitHub,
        onSuccess: (data) => {
            // Save current location for redirect after OAuth
            const currentPath = window.location.pathname;
            localStorage.setItem('github_oauth_redirect', currentPath);

            // Redirect to GitHub OAuth
            if (data.authorization_url) {
                window.location.href = data.authorization_url;
            } else if (data.auth_url) {
                // Fallback for different response format
                window.location.href = data.auth_url;
            }
        },
        onError: (error: any) => {
            console.error('Failed to connect GitHub:', error);
            // Error will be shown by the UI
        }
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => integrationsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['integrations'] });
        }
    });

    if (isLoading) {
        return (
            <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            </div>
        );
    }

    const githubIntegrations = integrations.filter(i => i.provider.toUpperCase() === 'GITHUB');
    const awsIntegrations = integrations.filter(i => i.provider.toUpperCase() === 'AWS');

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Integrations</h1>
                <p className="mt-2 text-gray-500 dark:text-gray-400">
                    Connect external services to enhance your security audits.
                </p>
            </div>

            {/* GitHub Integration */}
            <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-gray-900 dark:bg-white rounded-lg">
                                <Github className="h-6 w-6 text-white dark:text-gray-900" />
                            </div>
                            <div>
                                <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">GitHub</h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Connect your GitHub account to audit repositories
                                </p>
                            </div>
                        </div>
                        {githubIntegrations.length === 0 && (
                            <div className="flex flex-col items-end gap-2">
                                <Button
                                    onClick={() => connectGitHubMutation.mutate()}
                                    disabled={connectGitHubMutation.isPending || connectGitHubMutation.isSuccess}
                                >
                                    {connectGitHubMutation.isPending || connectGitHubMutation.isSuccess ? (
                                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Connecting...</>
                                    ) : (
                                        <><Plus className="mr-2 h-4 w-4" /> Connect GitHub</>
                                    )}
                                </Button>
                                {connectGitHubMutation.isError && (
                                    <p className="text-xs text-red-600 dark:text-red-400 max-w-xs text-right">
                                        {connectGitHubMutation.error?.response?.data?.error ||
                                            connectGitHubMutation.error?.message ||
                                            'Failed to connect. Please check your configuration.'}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {githubIntegrations.length > 0 ? (
                    <div className="p-6">
                        {githubIntegrations.map((integration) => (
                            <div key={integration.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    {integration.is_active ? (
                                        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                                    ) : (
                                        <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                                    )}
                                    <div>
                                        <div className="font-medium text-gray-900 dark:text-gray-100">{integration.name}</div>
                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                            Connected {new Date(integration.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                </div>
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    onClick={() => deleteMutation.mutate(integration.id)}
                                    disabled={deleteMutation.isPending}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="p-6">
                        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                            <Github className="h-12 w-12 mx-auto mb-3 opacity-50" />
                            <p>No GitHub integration connected</p>
                            <p className="text-sm mt-1">Connect GitHub to start auditing your repositories</p>
                        </div>
                    </div>
                )}
            </div>

            {/* AWS Integration */}
            <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="p-2 bg-orange-500 rounded-lg">
                                <Cloud className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">AWS</h2>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Connect AWS credentials for infrastructure audits
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {awsIntegrations.length > 0 ? (
                    <div className="p-6">
                        {awsIntegrations.map((integration) => (
                            <div key={integration.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    {integration.is_active ? (
                                        <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                                    ) : (
                                        <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                                    )}
                                    <div>
                                        <div className="font-medium text-gray-900 dark:text-gray-100">{integration.name}</div>
                                        <div className="text-sm text-gray-500 dark:text-gray-400">
                                            Connected {new Date(integration.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                </div>
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    onClick={() => deleteMutation.mutate(integration.id)}
                                    disabled={deleteMutation.isPending}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="p-6">
                        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
                            <Cloud className="h-12 w-12 mx-auto mb-3 opacity-50" />
                            <p>No AWS integration connected</p>
                            <p className="text-sm mt-1">Coming soon</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
