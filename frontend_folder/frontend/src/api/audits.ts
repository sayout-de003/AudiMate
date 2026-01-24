import { api } from './client';

export interface Audit {
    id: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
    created_at: string;
    completed_at?: string;
    pass_rate?: number;
}

export interface Evidence {
    id: number;
    check_id: string;
    status: 'PASS' | 'FAIL' | 'ERROR';
    resource_id: string;
    details: any;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    timestamp: string;
}

export const auditsApi = {
    list: async () => {
        const { data } = await api.get<{ organization: string; audit_count: number; audits: Audit[] }>('/audits/');
        // Backend returns { organization, audit_count, audits: [...] }
        // Extract the audits array
        return data.audits || [];
    },

    start: async () => {
        const { data } = await api.post<Audit>('/audits/start/');
        return data;
    },

    get: async (id: string) => {
        const { data } = await api.get<Audit>(`/audits/${id}/`);
        return data;
    },

    listEvidence: async (id: string) => {
        const { data } = await api.get<{ audit_id: string; organization: string; status: string; evidence_count: number; evidence: Evidence[] }>(`/audits/${id}/evidence/`);
        // Backend returns { audit_id, organization, status, evidence_count, evidence: [...] }
        // Extract the evidence array
        return data.evidence || [];
    },

    getSummary: async () => {
        const { data } = await api.get('/audits/dashboard/summary/');
        return data;
    },

    getStats: async () => {
        const { data } = await api.get('/audits/dashboard/stats/');
        return data;
    },

    exportCSV: async (id: string) => {
        const response = await api.get(`/audits/${id}/export/csv/`, { responseType: 'blob' });
        return response.data;
    },

    exportExcel: async (id: string) => {
        const response = await api.get(`/audits/${id}/export/xlsx/`, { responseType: 'blob' });
        return response.data;
    },

    uploadEvidence: async (auditId: string, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('audit_id', auditId);
        const { data } = await api.post('/audits/evidence/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return data;
    },

    getSnapshots: async (auditId: string) => {
        const { data } = await api.get(`/audits/${auditId}/snapshots/`);
        return data;
    },

    createSnapshot: async (auditId: string) => {
        const { data } = await api.post(`/audits/${auditId}/snapshots/create/`);
        return data;
    }
};
