import { type Evidence } from '../api/audits';
import { cn } from '../lib/utils';

export function EvidenceTable({ evidence }: { evidence: Evidence[] }) {
    if (evidence.length === 0) {
        return <div className="text-center py-8 text-gray-500">No evidence found.</div>;
    }

    return (
        <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Check ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Resource</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Severity</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 dark:bg-gray-900 dark:divide-gray-700">
                    {evidence.map((item) => (
                        <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{item.check_id}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300 font-mono">{item.resource_id}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className={cn(
                                    "px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full border",
                                    item.status === 'PASS' ? "bg-green-50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800" :
                                        item.status === 'FAIL' ? "bg-red-50 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800" :
                                            "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
                                )}>
                                    {item.status}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm">
                                <span className={cn(
                                    "font-medium",
                                    item.severity === 'CRITICAL' ? "text-red-600 dark:text-red-400" :
                                        item.severity === 'HIGH' ? "text-orange-600 dark:text-orange-400" :
                                            "text-gray-500"
                                )}>
                                    {item.severity}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
