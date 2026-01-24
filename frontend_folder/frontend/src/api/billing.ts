import { api } from './client';

export interface CheckoutSession {
    checkout_url: string;
    session_id: string;
}

export const billingApi = {
    createCheckoutSession: async (organizationId: string, priceId: string) => {
        const { data } = await api.post<CheckoutSession>('/billing/checkout_session/', {
            organization_id: organizationId,
            price_id: priceId
        });
        return data;
    }
};
