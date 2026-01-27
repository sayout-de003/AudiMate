import { useState } from 'react';
import { Button } from './ui/Button';
import { ShieldAlert, Loader2 } from 'lucide-react';
import { auditsApi } from '../api/audits';

interface RiskAcceptanceModalProps {
    isOpen: boolean;
    onClose: () => void;
    checkId: string;
    resourceId?: string;
    onSuccess: () => void;
}

export function RiskAcceptanceModal({ isOpen, onClose, checkId, resourceId, onSuccess }: RiskAcceptanceModalProps) {
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await auditsApi.acceptRisk(checkId, reason, resourceId);
            onSuccess();
            onClose();
        } catch (err: any) {
            setError(err.response?.data?.error || "Failed to accept risk.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6 m-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-full">
                        <ShieldAlert className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Accept Risk</h3>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Waive this check for {resourceId || 'the organization'}.</p>
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Justification (Required)
                        </label>
                        <textarea
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
                            rows={3}
                            placeholder="e.g., Legacy application, business requirement..."
                            required
                        />
                    </div>

                    {error && (
                        <div className="mb-4 p-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded">
                            {error}
                        </div>
                    )}

                    <div className="flex justify-end gap-3 mt-6">
                        <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading || !reason.trim()} className="bg-yellow-600 hover:bg-yellow-700 text-white">
                            {loading ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing</> : 'Confirm Risk Acceptance'}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
