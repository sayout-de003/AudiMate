import { api } from './client';

export const reportsApi = {
    generatePDF: async (auditId: string) => {
        // Endpoint on AuditViewSet is @action detail=True named 'pdf' -> /audits/{id}/pdf/
        const response = await api.get(`/audits/${auditId}/pdf/`, { responseType: 'blob' });
        return response.data;
    },

    previewPDF: async (auditId: string) => {
        const response = await api.get(`/audits/${auditId}/preview_pdf/`, { responseType: 'text' });
        return response.data;
    }
};
