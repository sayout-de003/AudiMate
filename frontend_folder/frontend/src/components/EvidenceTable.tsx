import { type Evidence } from '../api/audits';
import { EvidenceRow } from './EvidenceRow';

export function EvidenceTable({ evidence }: { evidence: Evidence[] }) {
    if (evidence.length === 0) {
        return (
            <div className="text-center py-12 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="text-gray-500 dark:text-gray-400 font-medium">No evidence found.</div>
                <p className="text-gray-400 text-sm mt-1">Run an audit to generate findings.</p>
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm bg-white dark:bg-gray-900">
            <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex justify-between items-center">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                    Audit Findings ({evidence.length})
                </h3>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {evidence.map((item) => (
                    <EvidenceRow key={item.id} evidence={item} />
                ))}
            </div>
        </div>
    );
}
