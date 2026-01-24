import { api } from './client';

export interface Organization {
    id: string; // UUID
    name: string;
    slug: string;
    created_at: string;
    role: string; // MEMBER, ADMIN, etc.
    subscription_status: 'free' | 'trial' | 'active' | 'past_due' | 'expired' | 'canceled';
    trial_end_date?: string;
    subscription_ends_at?: string;
}

export interface Member {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
}

export const orgsApi = {
    list: async () => {
        const { data } = await api.get<Organization[]>('/organizations/');
        return data;
    },

    create: async (name: string) => {
        const { data } = await api.post<Organization>('/organizations/', { name });
        return data;
    },

    get: async (id: string) => {
        const { data } = await api.get<Organization>(`/organizations/${id}/`);
        return data;
    },

    // Admin endpoints
    listMembers: async (id: string) => {
        const { data } = await api.get<Member[]>(`/organizations/${id}/admin/members/`);
        return data;
    },

    inviteMember: async (id: string, email: string) => {
        const { data } = await api.post(`/organizations/${id}/invite_member/`, { email, role: 'MEMBER' });
        return data;
    },

    update: async (id: string, updates: Partial<Omit<Organization, 'id' | 'created_at' | 'role' | 'slug'>>) => {
        const { data } = await api.patch<Organization>(`/organizations/${id}/`, updates);
        return data;
    },

    delete: async (id: string) => {
        await api.delete(`/organizations/${id}/`);
    },

    removeMember: async (orgId: string, userId: number) => {
        await api.delete(`/organizations/${orgId}/admin/members/${userId}/`);
    },

    getDashboard: async (id: string) => {
        const { data } = await api.get(`/organizations/${id}/admin/dashboard/`);
        return data;
    },

    getActivityLogs: async (id: string) => {
        const { data } = await api.get(`/organizations/${id}/admin/logs/`);
        return data;
    },

    getSettings: async (id: string) => {
        const { data } = await api.get(`/organizations/${id}/admin/settings/`);
        return data;
    }
};
