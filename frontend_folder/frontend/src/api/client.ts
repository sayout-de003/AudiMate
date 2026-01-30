import axios from 'axios';

const baseURL = 'http://localhost:8000/api/v1';

export const api = axios.create({
    baseURL,
    headers: {
        // Content-Type: application/json,  <-- Removed to let browser set it (for FormData) or defaults
    },
    withCredentials: true,
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Add Organization Context
        const orgId = localStorage.getItem('current_org_id');
        if (orgId) {
            config.headers['X-Organization-ID'] = orgId;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Optional: Handle token refresh logic here
        if (error.response?.status === 401) {
            // Clear storage and maybe redirect to login if not already there
            // localStorage.removeItem('access_token');
            // localStorage.removeItem('refresh_token');
            // window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);
