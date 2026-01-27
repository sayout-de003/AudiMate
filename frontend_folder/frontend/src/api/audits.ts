import { api } from './client';

export interface Audit {
    id: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
    created_at: string;
    completed_at?: string;
    pass_rate?: number;
}

export interface Question {
    id: number;
    key: string;
    title: string;
    description: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface Evidence {
    id: number;
    question: Question;
    status: 'PASS' | 'FAIL' | 'ERROR' | 'RISK_ACCEPTED';
    raw_data: any;
    comment?: string;
    created_at: string;
    screenshot_url: string | null;
    remediation_steps: string | null;
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

    exportPreview: async (id: string) => {
        const response = await api.get(`/audits/${id}/export/preview/`, { responseType: 'blob' });
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

    uploadEvidenceScreenshot: async (evidenceId: number, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('evidence_id', evidenceId.toString());
        const { data } = await api.post(`/audits/evidence/${evidenceId}/upload_screenshot/`, formData);
        return data;
    },

    getSnapshots: async (auditId: string) => {
        const { data } = await api.get(`/audits/${auditId}/snapshots/`);
        return data;
    },

    createSnapshot: async (auditId: string) => {
        const { data } = await api.post(`/audits/${auditId}/snapshots/create/`);
        return data;
    },

    acceptRisk: async (checkId: string, reason: string, resourceIdentifier?: string) => {
        const { data } = await api.post('/audits/risk-accept/', {
            check_id: checkId,
            reason,
            resource_identifier: resourceIdentifier
        });
        return data;
    }
};
