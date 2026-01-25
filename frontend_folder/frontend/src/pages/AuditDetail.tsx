import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { auditsApi } from '../api/audits';
import { reportsApi } from '../api/reports';
import { EvidenceTable } from '../components/EvidenceTable';
import { AuditStatus } from '../components/AuditStatus';
import { Button } from '../components/ui/Button';
import { ArrowLeft, Download, Loader2, FileText, Upload, Camera, Lock } from 'lucide-react';
import { cn } from '../lib/utils';
// import { useState } from 'react'; // Removed duplicate

type TabType = 'overview' | 'evidence' | 'snapshots';

export function AuditDetail() {
    const { id } = useParams<{ id: string }>();
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
    const [pollingEnabled, setPollingEnabled] = useState(false);
    const queryClient = useQueryClient();

    const { data: audit, isLoading: isLoadingAudit } = useQuery({
        queryKey: ['audit', id],
        queryFn: () => auditsApi.get(id!),
        refetchInterval: pollingEnabled ? 5000 : false,
    });

    // Enable polling if audit is running
    useEffect(() => {
        if (audit?.status === 'RUNNING' || audit?.status === 'PENDING') {
            setPollingEnabled(true);
        } else {
            setPollingEnabled(false);
        }
    }, [audit?.status]);

    const { data: evidence, isLoading: isLoadingEvidence } = useQuery({
        queryKey: ['audit-evidence', id],
        queryFn: () => auditsApi.listEvidence(id!)
    });

    const { data: snapshots, isLoading: isLoadingSnapshots } = useQuery({
        queryKey: ['audit-snapshots', id],
        queryFn: () => auditsApi.getSnapshots(id!),
        enabled: activeTab === 'snapshots'
    });

    const uploadEvidenceMutation = useMutation({
        mutationFn: (file: File) => auditsApi.uploadEvidence(id!, file),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['audit-evidence', id] });
            setEvidenceFile(null);
        }
    });

    const createSnapshotMutation = useMutation({
        mutationFn: () => auditsApi.createSnapshot(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['audit-snapshots', id] });
        }
    });

    const handleExportCSV = async () => {
        const blob = await auditsApi.exportCSV(id!);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-${id}-${Date.now()}.csv`;
        a.click();
    };

    const handleExportExcel = async () => {
        const blob = await auditsApi.exportExcel(id!);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-${id}-${Date.now()}.xlsx`;
        a.click();
    };

    const handleGeneratePDF = async () => {
        const blob = await reportsApi.generatePDF(id!);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit-report-${id}-${Date.now()}.pdf`;
        a.click();
    };

    const handlePreviewPDF = async () => {
        const htmlContent = await reportsApi.previewPDF(id!);
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank');
    };

    if (isLoadingAudit || isLoadingEvidence) {
        return <div className="flex justify-center p-12"><Loader2 className="h-8 w-8 animate-spin text-indigo-600" /></div>;
    }

    if (!audit) return <div>Audit not found</div>;

    const failureCount = evidence?.filter(e => e.status === 'FAIL').length || 0;
    const isCompleted = audit.status === 'COMPLETED';

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex items-center space-x-4">
                <Link to="/audits">
                    <Button variant="ghost" size="icon" className="rounded-full">
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                </Link>
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
                        Audit <span className="font-mono text-gray-500 text-lg">#{audit.id.slice(0, 8)}</span>
                    </h1>
                    <div className="flex items-center space-x-3 mt-1">
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                            Run on {new Date(audit.created_at).toLocaleString()}
                        </span>
                        <AuditStatus status={audit.status} />
                    </div>
                </div>

                {/* Export Buttons */}
                <div className="ml-auto flex items-center space-x-2">
                    <Button variant="outline" size="sm" onClick={handleExportCSV}>
                        <Download className="mr-2 h-4 w-4" />
                        CSV
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleExportExcel}>
                        <Download className="mr-2 h-4 w-4" />
                        Excel
                    </Button>
                    <Button variant="outline" size="sm" onClick={handlePreviewPDF} className="text-gray-600 border-gray-300 hover:bg-gray-50">
                        <FileText className="mr-2 h-4 w-4" />
                        Preview HTML
                    </Button>
                    <Button variant="default" size="sm" onClick={handleGeneratePDF} className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm">
                        <Download className="mr-2 h-4 w-4" />
                        Download PDF
                    </Button>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-6 md:grid-cols-4">
                {/* 1. Score */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700 flex flex-col justify-between">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Audit Score</div>
                    <div className={cn("mt-2 text-5xl font-black tracking-tighter",
                        (audit.score || 0) >= 90 ? "text-green-600" :
                            (audit.score || 0) >= 70 ? "text-yellow-600" : "text-red-600"
                    )}>
                        {audit.score !== undefined ? audit.score : '-'}
                        <span className="text-lg text-gray-400 font-normal ml-1">/100</span>
                    </div>
                </div>

                {/* 2. Grade */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Audit Grade</div>
                    <div className="mt-2 text-4xl font-extrabold text-gray-900 dark:text-indigo-400">
                        {audit.grade || '-'}
                    </div>
                </div>

                {/* 3. Total Checks */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Total Checks</div>
                    <div className="mt-2 text-4xl font-extrabold text-gray-900 dark:text-white">
                        {evidence?.length || 0}
                    </div>
                </div>

                {/* 4. Failures */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Failures</div>
                    <div className="mt-2 text-4xl font-extrabold text-red-600 dark:text-red-400">
                        {failureCount}
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 dark:border-gray-700">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={cn(
                            "py-4 px-1 border-b-2 font-medium text-sm transition-colors",
                            activeTab === 'overview'
                                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                        )}
                    >
                        Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('evidence')}
                        className={cn(
                            "py-4 px-1 border-b-2 font-medium text-sm transition-colors",
                            activeTab === 'evidence'
                                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                        )}
                    >
                        Evidence ({evidence?.length || 0})
                    </button>
                    <button
                        onClick={() => setActiveTab('snapshots')}
                        className={cn(
                            "py-4 px-1 border-b-2 font-medium text-sm transition-colors",
                            activeTab === 'snapshots'
                                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                        )}
                    >
                        Snapshots
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Evidence & Findings</h2>
                        {isCompleted && (
                            <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                                <Lock className="h-4 w-4 mr-2" />
                                Session Frozen
                            </div>
                        )}
                    </div>
                    <EvidenceTable evidence={evidence || []} />
                </div>
            )}

            {activeTab === 'evidence' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Evidence Management</h2>
                        {!isCompleted && (
                            <div className="flex items-center space-x-2">
                                <input
                                    type="file"
                                    id="evidence-upload"
                                    className="hidden"
                                    onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                                />
                                <label htmlFor="evidence-upload" className="cursor-pointer">
                                    <Button variant="outline" size="sm" type="button">
                                        <Upload className="mr-2 h-4 w-4" />
                                        Choose File
                                    </Button>
                                </label>
                                {evidenceFile && (
                                    <Button
                                        size="sm"
                                        onClick={() => uploadEvidenceMutation.mutate(evidenceFile)}
                                        disabled={uploadEvidenceMutation.isPending}
                                    >
                                        {uploadEvidenceMutation.isPending ? (
                                            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>
                                        ) : (
                                            `Upload ${evidenceFile.name}`
                                        )}
                                    </Button>
                                )}
                            </div>
                        )}
                    </div>
                    <EvidenceTable evidence={evidence || []} />
                </div>
            )}

            {activeTab === 'snapshots' && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Audit Snapshots</h2>
                        {!isCompleted && (
                            <Button
                                size="sm"
                                onClick={() => createSnapshotMutation.mutate()}
                                disabled={createSnapshotMutation.isPending}
                            >
                                {createSnapshotMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...</>
                                ) : (
                                    <><Camera className="mr-2 h-4 w-4" /> Create Snapshot</>
                                )}
                            </Button>
                        )}
                    </div>

                    {isLoadingSnapshots ? (
                        <div className="flex justify-center p-12">
                            <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                        </div>
                    ) : snapshots && snapshots.length > 0 ? (
                        <div className="grid gap-4">
                            {snapshots.map((snapshot: any) => (
                                <div key={snapshot.id} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <h3 className="font-medium text-gray-900 dark:text-gray-100">
                                                {snapshot.name || `Snapshot ${snapshot.id.slice(0, 8)}`}
                                            </h3>
                                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                                Created {new Date(snapshot.created_at).toLocaleString()}
                                            </p>
                                        </div>
                                        <Camera className="h-5 w-5 text-gray-400" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            <Camera className="h-12 w-12 mx-auto mb-3 opacity-50" />
                            <p>No snapshots created yet</p>
                            <p className="text-sm mt-1">Create a snapshot to preserve the current state</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
