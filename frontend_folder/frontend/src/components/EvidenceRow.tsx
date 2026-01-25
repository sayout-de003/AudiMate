import React, { useState } from 'react';
import { type Evidence, auditsApi } from '../api/audits';
import { cn } from '../lib/utils';
import { Camera, Code, AlertTriangle, CheckCircle, Info, Upload, RefreshCw, ShieldAlert, FileText } from 'lucide-react';
import { RiskAcceptanceModal } from './RiskAcceptanceModal';
import { Button } from './ui/Button';

interface EvidenceRowProps {
    evidence: Evidence;
}

export function EvidenceRow({ evidence: initialEvidence }: EvidenceRowProps) {
    const [evidence, setEvidence] = useState(initialEvidence);
    const [expanded, setExpanded] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    // Risk Acceptance State
    const [isRiskModalOpen, setIsRiskModalOpen] = useState(false);
    const [isAcceptingRisk, setIsAcceptingRisk] = useState(false);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        try {
            // Using the PATCH logic for manual_proof
            const updatedEvidence = await auditsApi.uploadEvidenceScreenshot(evidence.id, file); // note: name kept same but logic updated in api file

            setEvidence((prev: Evidence) => ({
                ...prev,
                manual_proof: updatedEvidence.manual_proof || updatedEvidence.screenshot_url || URL.createObjectURL(file),
                screenshot_url: updatedEvidence.screenshot_url || prev.screenshot_url // keep screenshot if exists
            }));

        } catch (error) {
            console.error("Upload failed", error);
            alert("Failed to upload proof.");
        } finally {
            setIsUploading(false);
        }
    };

    const handleAcceptRisk = async (reason: string) => {
        setIsAcceptingRisk(true);
        try {
            const updated = await auditsApi.acceptRisk(evidence.id, reason);
            setEvidence(updated); // Should return updated evidence with status='RISK_ACCEPTED'
            setIsRiskModalOpen(false);
        } catch (error) {
            alert("Failed to accept risk");
            console.error(error);
        } finally {
            setIsAcceptingRisk(false);
        }
    };

    const status = evidence.workflow_status || evidence.status; // Prefer workflow status if available

    return (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors first:border-t">
            {/* 1. Summary Row */}
            <div
                className="flex items-center justify-between p-4 cursor-pointer group"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-4">
                    <div className="flex-shrink-0">
                        {status === 'FAIL' ? (
                            <AlertTriangle className="text-red-500 w-5 h-5" />
                        ) : status === 'PASS' || status === 'FIXED' ? (
                            <CheckCircle className="text-green-500 w-5 h-5" />
                        ) : status === 'RISK_ACCEPTED' ? (
                            <ShieldAlert className="text-amber-500 w-5 h-5" />
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

                    {/* E. Action Buttons */}
                    <div className="mt-6 flex flex-wrap gap-3 border-t border-gray-100 dark:border-gray-700 pt-4">
                        {status !== 'RISK_ACCEPTED' && status !== 'PASS' && (
                            <Button
                                variant="outline"
                                size="sm"
                                className="text-amber-600 border-amber-200 hover:bg-amber-50"
                                onClick={() => setIsRiskModalOpen(true)}
                            >
                                <ShieldAlert className="w-4 h-4 mr-2" />
                                Accept Risk
                            </Button>
                        )}

                        {status === 'RISK_ACCEPTED' && (
                            <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded text-sm text-amber-800 dark:text-amber-200 w-full mb-2">
                                <span className="font-bold">Risk Accepted:</span> {evidence.risk_acceptance_reason}
                            </div>
                        )}
                    </div>
                </div>
            )}

            <RiskAcceptanceModal
                isOpen={isRiskModalOpen}
                onClose={() => setIsRiskModalOpen(false)}
                onConfirm={handleAcceptRisk}
                isLoading={isAcceptingRisk}
            />
        </div>
    );
}
