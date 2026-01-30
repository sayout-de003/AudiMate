import { cn } from '../lib/utils';
import { CheckCircle, XCircle, Clock, Loader2, Lock } from 'lucide-react';

export function AuditStatus({ status }: { status: string }) {
    const styles = {
        PENDING: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
        RUNNING: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
        COMPLETED: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
        FAILED: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
        FROZEN: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    };

    const icons = {
        PENDING: Clock,
        RUNNING: Loader2,
        COMPLETED: CheckCircle,
        FAILED: XCircle,
        FROZEN: Lock,
    };

    const Icon = icons[status as keyof typeof icons] || Clock;
    const style = styles[status as keyof typeof styles] || "bg-gray-100 text-gray-800";

    return (
        <span className={cn("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-transparent", style)}>
            <Icon className={cn("mr-1 h-3 w-3", status === 'RUNNING' && "animate-spin")} />
            {status}
        </span>
    );
}
