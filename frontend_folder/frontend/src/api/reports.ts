import { api } from './client';

export const reportsApi = {
    generatePDF: async (auditId: string) => {
        const response = await api.get(`/reports/${auditId}/pdf/`, { responseType: 'blob' });
        return response.data;
    }
};
