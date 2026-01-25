import React, { createContext, useContext, useEffect, useState } from 'react';
import { type User, authApi } from '../api/auth';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    login: (access: string, refresh: string) => void;
    logout: () => void;
    refetchUser: () => Promise<void>;
    isAuthenticated: boolean;
    hasOrganizations: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchUser = async () => {
        try {
            const token = localStorage.getItem('access_token');
            if (token) {
                const userData = await authApi.getMe();
                setUser(userData);
                // Store current organization ID for API client
                if (userData.current_organization) {
                    localStorage.setItem('current_org_id', userData.current_organization);
                }
            }
        } catch (error) {
            console.error('Failed to fetch user:', error);
            logout();
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchUser();
    }, []);

    const login = (access: string, refresh: string) => {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        fetchUser();
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_org_id');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{
            user,
            isLoading,
            login,
            logout,
            refetchUser: fetchUser,
            isAuthenticated: !!user,
            hasOrganizations: !!(user?.organizations && user.organizations.length > 0)
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
