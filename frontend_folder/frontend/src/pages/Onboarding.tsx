import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { orgsApi } from '../api/orgs';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { Building2, Loader2, AlertCircle } from 'lucide-react';

export function Onboarding() {
    const [orgName, setOrgName] = useState('');
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { refetchUser } = useAuth();

    const createOrgMutation = useMutation({
        mutationFn: (name: string) => orgsApi.create(name),
        onSuccess: async (data) => {
            console.log('Organization created successfully:', data);
            setErrorMessage(null);
            // Invalidate and refetch user data to update organizations list
            await queryClient.invalidateQueries({ queryKey: ['me'] });
            await queryClient.invalidateQueries({ queryKey: ['organizations'] });
            // Refetch auth context user data to update hasOrganizations
            await refetchUser();
            // Navigate to dashboard
            navigate('/', { replace: true });
        },
        onError: (error: any) => {
            console.error('Failed to create organization:', error);
            // Extract error message from response
            if (error?.response?.data) {
                const errorData = error.response.data;
                if (errorData.detail) {
                    if (typeof errorData.detail === 'object') {
                        // Handle field-specific errors
                        const fieldErrors = Object.entries(errorData.detail)
                            .map(([field, messages]: [string, any]) => {
                                const msg = Array.isArray(messages) ? messages[0] : messages;
                                return `${field}: ${msg}`;
                            })
                            .join(', ');
                        setErrorMessage(fieldErrors || 'Failed to create organization');
                    } else {
                        setErrorMessage(String(errorData.detail));
                    }
                } else if (errorData.message) {
                    setErrorMessage(errorData.message);
                } else if (errorData.name) {
                    setErrorMessage(`Organization name: ${Array.isArray(errorData.name) ? errorData.name[0] : errorData.name}`);
                } else {
                    setErrorMessage('Failed to create organization. Please try again.');
                }
            } else {
                setErrorMessage('Failed to create organization. Please check your connection and try again.');
            }
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setErrorMessage(null);
        if (orgName.trim()) {
            console.log('Creating organization with name:', orgName.trim());
            createOrgMutation.mutate(orgName.trim());
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center p-4">
            <div className="max-w-md w-full">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-600 rounded-2xl mb-4">
                        <Building2 className="h-8 w-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                        Create Your Organization
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400">
                        Let's get started by creating your first organization
                    </p>
                </div>

                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label
                                htmlFor="orgName"
                                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                            >
                                Organization Name
                            </label>
                            <input
                                id="orgName"
                                type="text"
                                value={orgName}
                                onChange={(e) => setOrgName(e.target.value)}
                                placeholder="e.g., Acme Corporation"
                                required
                                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                                disabled={createOrgMutation.isPending}
                            />
                        </div>

                        {(createOrgMutation.isError || errorMessage) && (
                            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                                <div className="flex items-start">
                                    <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mr-2 flex-shrink-0 mt-0.5" />
                                    <p className="text-sm text-red-600 dark:text-red-400">
                                        {errorMessage || 'Failed to create organization. Please try again.'}
                                    </p>
                                </div>
                            </div>
                        )}

                        <Button
                            type="submit"
                            className="w-full"
                            disabled={!orgName.trim() || createOrgMutation.isPending}
                        >
                            {createOrgMutation.isPending ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    <Building2 className="mr-2 h-4 w-4" />
                                    Create Organization
                                </>
                            )}
                        </Button>
                    </form>
                </div>

                <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
                    You'll be assigned as the administrator of this organization
                </p>
            </div>
        </div>
    );
}
