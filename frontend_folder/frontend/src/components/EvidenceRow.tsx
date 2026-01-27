import React, { useState } from 'react';
import { type Evidence, auditsApi } from '../api/audits';
import { cn } from '../lib/utils';
import { Camera, Code, AlertTriangle, CheckCircle, Info, Upload, RefreshCw } from 'lucide-react';
import { RiskAcceptanceModal } from './RiskAcceptanceModal';

interface EvidenceRowProps {
    evidence: Evidence;
}

export function EvidenceRow({ evidence: initialEvidence }: EvidenceRowProps) {
    const [evidence, setEvidence] = useState(initialEvidence);
    const [expanded, setExpanded] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [showRiskModal, setShowRiskModal] = useState(false);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        try {
            const updatedEvidence = await auditsApi.uploadEvidenceScreenshot(evidence.id, file);
            // Optimistic update or use returned data if backend returns the updated evidence object
            // Assuming backend returns { success: true, url: ... } or the updated evidence object.
            // Let's assume it returns the updated evidence or we force a refresh.
            // Adjust based on API response. If API returns just success, we might fallback to object URL for immediate feedback.
            setEvidence((prev: Evidence) => ({
                ...prev,
                screenshot_url: updatedEvidence.screenshot_url || URL.createObjectURL(file)
            }));
        } catch (error) {
            console.error("Upload failed", error);
            alert("Failed to upload screenshot.");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors first:border-t">
            {/* 1. Summary Row */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer group"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-4">
                    <div className="flex-shrink-0">
                        {evidence.status === 'FAIL' ? (
                            <AlertTriangle className="text-red-500 w-5 h-5" />
                        ) : evidence.status === 'PASS' ? (
                            <CheckCircle className="text-green-500 w-5 h-5" />
                        ) : (
                            <Info className="text-gray-500 w-5 h-5" />
                        )}
                    </div>
                    <div>
                        <div className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                            {evidence.question?.title || 'Unknown Check'}
                        </div>
                        <div className="text-xs text-gray-500 font-mono mt-0.5">{evidence.question?.key || 'N/A'}</div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <span className={cn(
                        "px-2 py-1 rounded text-xs font-bold",
                        evidence.question?.severity === 'CRITICAL' ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300" :
                            evidence.question?.severity === 'HIGH' ? "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300" :
                                evidence.question?.severity === 'MEDIUM' ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300" :
                                    "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                    )}>
                        {evidence.question?.severity || 'UNKNOWN'}
                    </span>
                    <span className="text-blue-600 dark:text-blue-400 text-sm hover:underline hidden sm:inline-block">
                        {expanded ? 'Hide Proof' : 'View Proof'}
                    </span>
                </div>
            </div>

            {/* 2. Expanded Detail Panel */}
            {expanded && (
                <div className="bg-gray-50 dark:bg-gray-800/50 p-6 border-t border-gray-200 dark:border-gray-700 pl-12 animate-in slide-in-from-top-2 duration-200">

                    {/* A. Screenshot Section */}
                    <div className="mb-6">
                        <h4 className="flex items-center gap-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                            <Camera size={14} /> Evidence Screenshot
                        </h4>
                        {evidence.screenshot_url ? (
                            <div className="relative group">
                                <div className="border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm overflow-hidden max-w-2xl bg-white dark:bg-gray-900">
                                    <img
                                        src={evidence.screenshot_url}
                                        alt="Audit Proof"
                                        className="w-full h-auto object-contain cursor-zoom-in hover:opacity-95 transition-opacity"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            window.open(evidence.screenshot_url!, '_blank');
                                        }}
                                    />
                                </div>
                                <div className="mt-2">
                                    <label className="cursor-pointer inline-flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 hover:underline">
                                        <RefreshCw size={12} /> Replace Screenshot
                                        <input
                                            type="file"
                                            className="hidden"
                                            accept="image/*"
                                            onChange={handleFileUpload}
                                            disabled={isUploading}
                                        />
                                    </label>
                                </div>
                            </div>
                        ) : (
                            <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                                <Upload className="w-8 h-8 text-gray-400 mb-2" />
                                <p className="text-sm text-gray-500 font-medium mb-1">No automated screenshot available.</p>
                                <label className={cn(
                                    "mt-2 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center gap-2",
                                    isUploading && "opacity-50 cursor-not-allowed"
                                )}>
                                    {isUploading ? "Uploading..." : "Upload Manual Proof"}
                                    <input
                                        type="file"
                                        className="hidden"
                                        accept="image/*"
                                        onChange={handleFileUpload}
                                        disabled={isUploading}
                                    />
                                </label>
                                <p className="text-xs text-gray-400 mt-2">PNG, JPG up to 5MB</p>
                            </div>
                        )}
                    </div>

                    {/* B. Raw Data / Logs Section */}
                    {evidence.raw_data && (
                        <div className="mb-6">
                            <h4 className="flex items-center gap-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                                <Code size={14} /> System Evidence (JSON/Log)
                            </h4>
                            <div className="bg-slate-950 rounded-lg p-4 overflow-x-auto shadow-inner border border-slate-800">
                                <pre className="text-emerald-400 font-mono text-xs leading-relaxed">
                                    {typeof evidence.raw_data === 'string' ? evidence.raw_data : JSON.stringify(evidence.raw_data, null, 2)}
                                </pre>
                            </div>
                        </div>
                    )}

                    {/* C. Remediation */}
                    {evidence.status === 'FAIL' && (
                        <div className="bg-red-50 dark:bg-red-900/10 border-l-4 border-red-500 p-4 rounded-r">
                            <h4 className="text-red-800 dark:text-red-400 font-bold text-sm">Recommended Remediation</h4>
                            <div className="text-red-700 dark:text-red-300 text-sm mt-1 prose prose-sm max-w-none">
                                {evidence.remediation_steps ? (
                                    <div className="whitespace-pre-wrap font-sans">{evidence.remediation_steps}</div>
                                ) : (
                                    "Consult security documentation or contact the security team."
                                )}
                            </div>
                        </div>
                    )}

                    {/* D. Risk Acceptance (New) */}
                    {(evidence.status === 'FAIL') && (
                        <div className="mt-6 border-t border-gray-200 dark:border-gray-700 pt-4 flex justify-end">
                            <RiskAcceptanceModal
                                isOpen={showRiskModal}
                                onClose={() => setShowRiskModal(false)}
                                checkId={evidence.question.key}
                                resourceId={evidence.raw_data?.repo_name || undefined}
                                onSuccess={() => {
                                    setEvidence(prev => ({ ...prev, status: 'RISK_ACCEPTED', comment: (prev.comment || '') + ' [RISK ACCEPTED]' }));
                                }}
                            />
                            <button
                                onClick={() => setShowRiskModal(true)}
                                className="text-sm text-yellow-600 dark:text-yellow-500 hover:text-yellow-700 dark:hover:text-yellow-400 font-medium flex items-center gap-1"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-shield-alert"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M12 8v4" /><path d="M12 16h.01" /></svg>
                                Accept Risk / Waive
                            </button>
                        </div>
                    )}

                    {/* E. Comment */}
                    {evidence.comment && (
                        <div className="mt-4 text-sm text-gray-600 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-4">
                            <span className="font-semibold">Note:</span> {evidence.comment}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
