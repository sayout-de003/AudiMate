import { api } from './client';

export interface Integration {
    id: string;
    provider: 'GITHUB' | 'AWS' | 'github' | 'aws';  // Accept both cases
    name: string;
    created_at: string;
    status: 'active' | 'disconnected' | 'error';
    external_id: string;
    config: any;
}

export interface IntegrationData {
    provider: 'GITHUB' | 'AWS' | 'github' | 'aws';  // Accept both cases
    name: string;
    access_token: string;
}

export const integrationsApi = {
    list: async () => {
        const { data } = await api.get<Integration[]>('/integrations/');
        return data;
    },

    create: async (integrationData: IntegrationData) => {
        const { data } = await api.post<Integration>('/integrations/', integrationData);
        return data;
    },

    get: async (id: string) => {
        const { data } = await api.get<Integration>(`/integrations/${id}/`);
        return data;
    },

    update: async (id: string, updates: Partial<IntegrationData>) => {
        const { data } = await api.patch<Integration>(`/integrations/${id}/`, updates);
        return data;
    },

    delete: async (id: string) => {
        await api.delete(`/integrations/${id}/`);
    },

    connectGitHub: async () => {
        const { data } = await api.get('/integrations/github/connect/');
        return data;
    },

    handleCallback: async (code: string, state?: string) => {
        const { data } = await api.post('/integrations/github/callback/', {
            code,
            ...(state && { state })
        });
        return data;
    }
};
