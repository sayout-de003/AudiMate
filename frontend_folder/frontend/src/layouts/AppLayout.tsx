import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShieldCheck, LogOut, Building2, Plug, User, CreditCard } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { cn } from '../lib/utils';

export function AppLayout() {
    const { user, logout } = useAuth();
    const location = useLocation();

    const navigation = [
        { name: 'Dashboard', href: '/', icon: LayoutDashboard },
        { name: 'Audits', href: '/audits', icon: ShieldCheck },
        { name: 'Integrations', href: '/integrations', icon: Plug },
        { name: 'Organization', href: '/settings', icon: Building2 },
        { name: 'Billing', href: '/billing', icon: CreditCard },
        { name: 'Profile', href: '/profile', icon: User },
    ];

    return (
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900 font-sans">
            {/* Sidebar */}
            <div className="hidden md:flex md:w-72 md:flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
                <div className="flex items-center h-20 px-8 border-b border-gray-100 dark:border-gray-700">
                    <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                        AuditEase
                    </span>
                </div>

                <div className="flex-1 flex flex-col p-6 space-y-2">
                    <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-2">
                        Menu
                    </div>
                    {navigation.map((item) => {
                        const Icon = item.icon;
                        const isActive = location.pathname === item.href || (item.href !== '/' && location.pathname.startsWith(item.href));
                        return (
                            <Link
                                key={item.name}
                                to={item.href}
                                className={cn(
                                    "flex items-center px-4 py-3 text-sm font-medium rounded-xl transition-all duration-200 group",
                                    isActive
                                        ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400 shadow-sm"
                                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-700/50 dark:hover:text-gray-200"
                                )}
                            >
                                <Icon className={cn("mr-3 h-5 w-5 transition-colors", isActive ? "text-indigo-600 dark:text-indigo-400" : "text-gray-400 group-hover:text-gray-500")} />
                                {item.name}
                            </Link>
                        )
                    })}
                </div>

                <div className="p-6 border-t border-gray-100 dark:border-gray-700">
                    <div className="flex items-center mb-6">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-md">
                            {user?.first_name?.[0]}{user?.last_name?.[0]}
                        </div>
                        <div className="ml-3 overflow-hidden">
                            <p className="text-sm font-semibold text-gray-700 dark:text-gray-200 truncate">
                                {user?.first_name} {user?.last_name}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {user?.email}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors duration-200"
                    >
                        <LogOut className="mr-2 h-4 w-4" />
                        Sign Out
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
                <main className="p-8 max-w-7xl mx-auto">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
