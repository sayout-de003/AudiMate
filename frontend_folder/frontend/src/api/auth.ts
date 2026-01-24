import { api } from './client';

export interface User {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    current_organization?: string; // UUID or ID
    organizations?: Array<{ id: string; name: string; role: string }>; // For onboarding check
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
    password_confirm?: string;
    first_name: string;
    last_name: string;
}

export interface AuthResponse {
    access: string;
    refresh: string;
    user?: User;
}

export const authApi = {
    login: async (credentials: LoginCredentials) => {
        const { data } = await api.post<AuthResponse>('/auth/login/', credentials);
        return data;
    },

    register: async (data: RegisterData) => {
        const { data: response } = await api.post('/auth/register/', data);
        return response;
    },

    getMe: async () => {
        const { data } = await api.get<User>('/users/me/');
        return data;
    },

    refreshToken: async (refresh: string) => {
        const { data } = await api.post('/auth/refresh/', { refresh });
        return data;
    },

    changePassword: async (oldPassword: string, newPassword: string) => {
        const { data } = await api.post('/auth/password/change/', {
            old_password: oldPassword,
            new_password: newPassword
        });
        return data;
    },

    resetPassword: async (email: string) => {
        const { data } = await api.post('/auth/password/reset/', { email });
        return data;
    },

    confirmPasswordReset: async (uid: string, token: string, newPassword: string) => {
        const { data } = await api.post('/auth/password/reset/confirm/', {
            uid,
            token,
            new_password1: newPassword,
            new_password2: newPassword
        });
        return data;
    },

    updateProfile: async (updates: { first_name?: string; last_name?: string }) => {
        const { data } = await api.patch('/users/me/', updates);
        return data;
    },

    verifyEmail: async (email: string, otpCode: string) => {
        const { data } = await api.post('/auth/verify-email/', {
            email,
            otp_code: otpCode
        });
        return data;
    },

    resendOTP: async (email: string) => {
        const { data } = await api.post('/auth/resend-otp/', { email });
        return data;
    }
};
