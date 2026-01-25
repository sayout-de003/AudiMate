import { api } from './client';

export interface Audit {
    id: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
    score: number;
    grade: string;
    created_at: string;
    completed_at?: string;
    details?: {
        critical_fails: number;
        high_fails: number;
        pass_count: number;
        [key: string]: any;
    };
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
    status: 'PASS' | 'FAIL' | 'ERROR';
    raw_data: any;
    comment?: string;
    created_at: string;
    screenshot_url: string | null;
    manual_proof: string | null;
    remediation_steps: string | null;
    workflow_status?: 'OPEN' | 'FIXED' | 'RISK_ACCEPTED';
    risk_acceptance_reason?: string;
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

    uploadEvidenceScreenshot: async (evidenceId: number, file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('evidence_id', evidenceId.toString());
        // Use generic upload endpoint if specific one doesn't exist, or specific one
        // Assuming endpoint /api/v1/evidence/{id}/upload_proof/ or similar based on request
        // The prompt asked for: PATCH /api/v1/evidence/{id}/ with multipart/form-data for manual_proof field
        // So let's implement the PATCH method
        const patchFormData = new FormData();
        patchFormData.append('manual_proof', file);

        const { data } = await api.patch(`/evidence/${evidenceId}/`, patchFormData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return data;
    },

    acceptRisk: async (evidenceId: number, reason: string) => {
        const { data } = await api.post(`/evidence/${evidenceId}/accept_risk/`, { reason });
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
