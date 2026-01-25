import { useState } from 'react';
import { Button } from './ui/Button';
import { Loader2, AlertTriangle } from 'lucide-react';

interface RiskAcceptanceModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (reason: string) => Promise<void>;
    isLoading: boolean;
}

export function RiskAcceptanceModal({ isOpen, onClose, onConfirm, isLoading }: RiskAcceptanceModalProps) {
    const [reason, setReason] = useState('');
    const [error, setError] = useState('');

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (reason.trim().length < 10) {
            setError('Please provide a descriptive reason (at least 10 characters).');
            return;
        }
        setError('');
        await onConfirm(reason);
        setReason(''); // Reset after success
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700 animate-in zoom-in-95 duration-200">
                <div className="flex items-center space-x-2 text-amber-600 mb-4">
                    <AlertTriangle className="h-6 w-6" />
                    <h2 className="text-lg font-bold">Accept Risk</h2>
                </div>

                <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    You are marking this finding as <strong>Risk Accepted</strong>.
                    This will exclude it from the audit score deduction.
                    A valid reason is required for compliance tracking.
                </p>

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label htmlFor="reason" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Reason for Acceptance
                        </label>
                        <textarea
                            id="reason"
                            rows={4}
                            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
                            placeholder="e.g., Mitigating control in place via WAF; Legacy system to be decommissioned in Q4..."
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            disabled={isLoading}
                        />
                        {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
                    </div>

                    <div className="flex justify-end space-x-2">
                        <Button variant="ghost" type="button" onClick={onClose} disabled={isLoading}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading} className="bg-amber-600 hover:bg-amber-700 text-white">
                            {isLoading ? (
                                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing</>
                            ) : (
                                'Accept Risk'
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
