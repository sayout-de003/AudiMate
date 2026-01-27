import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { auditsApi } from '../api/audits';
import { integrationsApi } from '../api/integrations';
import { Activity, CheckCircle2, AlertTriangle, Shield, Loader2, Github } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function Dashboard() {
    const navigate = useNavigate();

    const { data: summary, isLoading: summaryLoading, isError: summaryError } = useQuery({
        queryKey: ['dashboard-summary'],
        queryFn: auditsApi.getSummary,
        retry: false,
        refetchInterval: 30000, // Refresh every 30 seconds
        throwOnError: false
    });

    const { data: recentAudits, isLoading: auditsLoading, isError: auditsError } = useQuery({
        queryKey: ['audits'],
        queryFn: auditsApi.list,
        retry: false,
        throwOnError: false
    });

    const { data: integrations = [] } = useQuery({
        queryKey: ['integrations'],
        queryFn: integrationsApi.list
    });

    const githubIntegration = integrations.find(i => i.provider.toUpperCase() === 'GITHUB' && i.is_active);
    const hasGitHub = !!githubIntegration;
    const latestAudits = recentAudits?.slice(0, 5) || [];

    if (summaryLoading || auditsLoading) {
        return (
            <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Dashboard</h1>
                <p className="mt-2 text-gray-500 dark:text-gray-400">Overview of your organization's security posture.</p>
            </div>

            {/* GitHub Connection Banner */}
            {!hasGitHub && (
                <div className="rounded-xl border border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-800 p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                        <div>
                            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                                GitHub integration required
                            </p>
                            <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-0.5">
                                Connect your GitHub account to start running security audits
                            </p>
                        </div>
                    </div>
                    <Button
                        size="sm"
                        onClick={() => navigate('/integrations')}
                        className="bg-yellow-600 hover:bg-yellow-700 text-white"
                    >
                        <Github className="mr-2 h-4 w-4" />
                        Connect GitHub
                    </Button>
                </div>
            )}

            {/* Stat Cards */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <StatCard
                    icon={Activity}
                    title="Total Audits"
                    value={summary?.total_audits || 0}
                    subtitle={`${summary?.completed_audits || 0} completed`}
                    iconColor="text-blue-600"
                    bgColor="bg-blue-50 dark:bg-blue-900/20"
                />
                <StatCard
                    icon={CheckCircle2}
                    title="Pass Rate"
                    value={summary?.pass_rate ? `${summary.pass_rate.toFixed(1)}%` : '0%'}
                    subtitle="Overall compliance"
                    iconColor="text-green-600"
                    bgColor="bg-green-50 dark:bg-green-900/20"
                />
                <StatCard
                    icon={AlertTriangle}
                    title="Critical Issues"
                    value={summary?.critical_issues || 0}
                    subtitle="Requires attention"
                    iconColor="text-red-600"
                    bgColor="bg-red-50 dark:bg-red-900/20"
                />
                <StatCard
                    icon={Shield}
                    title="Resources Checked"
                    value={summary?.resources_checked || 0}
                    subtitle="In last 30 days"
                    iconColor="text-purple-600"
                    bgColor="bg-purple-50 dark:bg-purple-900/20"
                />
            </div>

            {/* Compliance Trend Chart */}
            <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-6">Compliance Trend (30 Days)</h3>
                <div className="h-[300px] w-full">
                    {summary?.history && summary.history.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={summary.history}>
                                <defs>
                                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" opacity={0.2} />
                                <XAxis
                                    dataKey="date"
                                    tickFormatter={(str) => new Date(str).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                    stroke="#9ca3af"
                                    tick={{ fontSize: 12 }}
                                    tickLine={false}
                                    axisLine={false}
                                />
                                <YAxis
                                    domain={[0, 100]}
                                    stroke="#9ca3af"
                                    tick={{ fontSize: 12 }}
                                    tickLine={false}
                                    axisLine={false}
                                    tickFormatter={(value) => `${value}%`}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                    itemStyle={{ color: '#e5e7eb' }}
                                    formatter={(value: number | undefined) => [`${value}%`, 'Score']}
                                    labelFormatter={(label) => new Date(label).toLocaleDateString()}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="score"
                                    stroke="#4f46e5"
                                    strokeWidth={3}
                                    fillOpacity={1}
                                    fill="url(#colorScore)"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="flex h-full items-center justify-center text-gray-400">
                            <p>No history data available yet.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Recent Audits */}
            <div className="rounded-xl border border-gray-100 bg-white shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
                    <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">Recent Audits</h3>
                    <Button onClick={() => navigate('/audits')} size="sm">View All</Button>
                </div>
                <div className="p-6">
                    {latestAudits.length > 0 ? (
                        <div className="space-y-4">
                            {latestAudits.map((audit) => (
                                <div
                                    key={audit.id}
                                    onClick={() => navigate(`/audits/${audit.id}`)}
                                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-all"
                                >
                                    <div className="flex items-center space-x-4">
                                        <div className={`h-2 w-2 rounded-full ${audit.status === 'COMPLETED' ? 'bg-green-500' :
                                            audit.status === 'RUNNING' ? 'bg-blue-500 animate-pulse' :
                                                audit.status === 'FAILED' ? 'bg-red-500' :
                                                    'bg-gray-400'
                                            }`} />
                                        <div>
                                            <div className="font-medium text-gray-900 dark:text-gray-100">
                                                Audit #{audit.id.slice(0, 8)}
                                            </div>
                                            <div className="text-sm text-gray-500 dark:text-gray-400">
                                                {new Date(audit.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        {audit.pass_rate !== undefined && (
                                            <div className="text-right">
                                                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                                                    {audit.pass_rate.toFixed(1)}% Pass
                                                </div>
                                            </div>
                                        )}
                                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${audit.status === 'COMPLETED' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                                            audit.status === 'RUNNING' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                                                audit.status === 'FAILED' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                                                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                            }`}>
                                            {audit.status}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-[200px] flex flex-col items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50">
                            <Activity className="h-12 w-12 mb-3 text-gray-300" />
                            <span className="mb-2">No audits run yet</span>
                            <Button onClick={() => navigate('/audits')} size="sm">
                                Start your first audit
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatCard({ icon: Icon, title, value, subtitle, iconColor, bgColor }: {
    icon: any;
    title: string;
    value: string | number;
    subtitle: string;
    iconColor: string;
    bgColor: string;
}) {
    return (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm hover:shadow-md transition-shadow dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</div>
                    <div className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2">{value}</div>
                    <div className="text-xs text-gray-400 mt-1">{subtitle}</div>
                </div>
                <div className={`${bgColor} p-3 rounded-lg`}>
                    <Icon className={`h-6 w-6 ${iconColor}`} />
                </div>
            </div>
        </div>
    );
}
