import { Outlet } from 'react-router-dom';

export function AuthLayout() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4 font-sans">
            <div className="w-full max-w-md space-y-8">
                <div className="text-center">
                    <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white">
                        AuditEase
                    </h1>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                        Enterprise Integrated Compliance & Security
                    </p>
                </div>
                <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-gray-100 dark:border-gray-700">
                    <Outlet />
                </div>
            </div>
        </div>
    );
}
