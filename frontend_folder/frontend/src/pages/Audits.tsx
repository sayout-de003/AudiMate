import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { auditsApi } from '../api/audits';
import { integrationsApi } from '../api/integrations';
import { Button } from '../components/ui/Button';
import { AuditStatus } from '../components/AuditStatus';
import { Play, FileText, Loader2, AlertCircle, Github } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { cn } from '../lib/utils';

export function Audits() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();
    const [pollingEnabled, setPollingEnabled] = useState(false);

    const { data: audits, isLoading } = useQuery({
        queryKey: ['audits'],
        queryFn: auditsApi.list,
        refetchInterval: pollingEnabled ? 5000 : false, // Poll every 5 seconds when enabled
    });

    const { data: integrations = [] } = useQuery({
        queryKey: ['integrations'],
        queryFn: integrationsApi.list
    });

    const githubIntegration = integrations.find(i => i.provider.toUpperCase() === 'GITHUB' && i.status === 'active');
    const hasGitHub = !!githubIntegration;

    // Check if there's a running audit and enable polling
    useEffect(() => {
        const hasRunningAudit = audits?.some(a => a.status === 'RUNNING' || a.status === 'PENDING');
        setPollingEnabled(hasRunningAudit || false);
    }, [audits]);

    const startAuditMutation = useMutation({
        mutationFn: auditsApi.start,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['audits'] });
            setPollingEnabled(true); // Start polling after starting audit
        },
        onError: (error: any) => {
            console.error('Failed to start audit:', error);
        }
    });

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Audits</h1>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">Manage and run security compliance audits.</p>
                </div>
                <div className="flex items-center gap-3">
                    {!hasGitHub && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                            <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                            <span className="text-sm text-yellow-700 dark:text-yellow-300">Connect GitHub to start audits</span>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate('/integrations')}
                                className="ml-2"
                            >
                                <Github className="mr-2 h-4 w-4" />
                                Connect
                            </Button>
                        </div>
                    )}
                    <Button
                        onClick={() => startAuditMutation.mutate()}
                        disabled={startAuditMutation.isPending || !hasGitHub}
                        title={!hasGitHub ? 'Please connect GitHub first' : ''}
                    >
                        {startAuditMutation.isPending ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Starting...
                            </>
                        ) : (
                            <>
                                <Play className="mr-2 h-4 w-4" />
                                Start Audit
                            </>
                        )}
                    </Button>
                </div>
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
                {isLoading ? (
                    <div className="p-12 text-center flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>
                ) : audits?.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        <div className="mb-4">No audits found.</div>
                        <Button variant="outline" onClick={() => startAuditMutation.mutate()}>Run your first audit</Button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-900/50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Status</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Score</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Grade</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200 dark:bg-gray-800 dark:divide-gray-700">
                                {audits?.map((audit) => (
                                    <tr key={audit.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap font-mono text-xs text-gray-500 dark:text-gray-400">{audit.id.slice(0, 8)}...</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">
                                            {new Date(audit.created_at).toLocaleDateString()} <span className="text-gray-400 text-xs ml-1">{new Date(audit.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <AuditStatus status={audit.status} />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                            {(audit.status === 'RUNNING' || audit.status === 'PENDING') ? (
                                                <div className="flex items-center text-indigo-600">
                                                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                                    <span className="text-xs font-medium">Scanning...</span>
                                                </div>
                                            ) : (
                                                <span className={cn(
                                                    "font-bold text-lg",
                                                    audit.score >= 80 ? "text-green-600" : audit.score >= 50 ? "text-yellow-600" : "text-red-600"
                                                )}>
                                                    {audit.score}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {(audit.status === 'RUNNING' || audit.status === 'PENDING') ? (
                                                <span className="text-gray-300">-</span>
                                            ) : (
                                                <span className={cn(
                                                    "inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold text-white shadow-sm",
                                                    audit.grade === 'A' ? "bg-green-500" :
                                                        audit.grade === 'B' ? "bg-blue-500" :
                                                            audit.grade === 'C' ? "bg-yellow-500" : "bg-red-500"
                                                )}>
                                                    {audit.grade}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <Link to={`/audits/${audit.id}`} className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 inline-flex items-center transition-colors">
                                                Details <FileText className="ml-1 h-3 w-3" />
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
