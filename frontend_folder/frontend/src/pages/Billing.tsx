import { useQuery } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { orgsApi } from '../api/orgs';
import { billingApi } from '../api/billing';
import { Button } from '../components/ui/Button';
import { Loader2, CreditCard, Check, X } from 'lucide-react';

export function Billing() {
    const { data: user } = useQuery({
        queryKey: ['me'],
        queryFn: authApi.getMe
    });

    const currentOrgId = user?.current_organization || user?.organizations?.[0]?.id;

    const { data: organization, isLoading } = useQuery({
        queryKey: ['organization', currentOrgId],
        queryFn: () => orgsApi.get(currentOrgId!),
        enabled: !!currentOrgId
    });

    const handleUpgrade = async (priceId: string) => {
        try {
            const { checkout_url } = await billingApi.createCheckoutSession(currentOrgId!, priceId);
            window.location.href = checkout_url;
        } catch (error) {
            console.error('Failed to create checkout session:', error);
            alert('Failed to create checkout session. Please try again.');
        }
    };

    if (isLoading) {
        return (
            <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            </div>
        );
    }

    const isActive = organization?.subscription_status === 'active';
    const isTrial = organization?.subscription_status === 'trial';
    const isFree = organization?.subscription_status === 'free';
    const needsUpgrade = isFree || isTrial || 
        organization?.subscription_status === 'expired' || 
        organization?.subscription_status === 'canceled' || 
        organization?.subscription_status === 'past_due';

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Billing & Subscription</h1>
                <p className="mt-2 text-gray-500 dark:text-gray-400">Manage your subscription and billing information.</p>
            </div>

            {/* Current Plan */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center">
                        <CreditCard className="mr-2 h-5 w-5" />
                        Current Plan
                    </h2>
                </div>

                <div className="space-y-4">
                    <div>
                        <div className="flex items-center space-x-2">
                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${isActive ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                                isTrial ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                                    organization?.subscription_status === 'past_due' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' :
                                        (organization?.subscription_status === 'expired' || organization?.subscription_status === 'canceled') ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                                            'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                }`}>
                                {organization?.subscription_status === 'free' && 'Free Plan'}
                                {organization?.subscription_status === 'trial' && 'Trial'}
                                {organization?.subscription_status === 'active' && 'Pro Plan'}
                                {organization?.subscription_status === 'past_due' && 'Past Due'}
                                {organization?.subscription_status === 'expired' && 'Expired'}
                                {organization?.subscription_status === 'canceled' && 'Canceled'}
                            </span>
                        </div>
                    </div>

                    {organization?.trial_end_date && isTrial && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                <strong>Trial ends:</strong> {new Date(organization.trial_end_date).toLocaleDateString()}
                            </p>
                        </div>
                    )}

                    {(organization?.subscription_status === 'expired' || organization?.subscription_status === 'canceled' || organization?.subscription_status === 'past_due') && (
                        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <p className="text-sm text-red-700 dark:text-red-300">
                                <strong>Action Required:</strong> Your subscription needs attention. Please upgrade to continue using all features.
                            </p>
                        </div>
                    )}

                    {organization?.subscription_ends_at && isActive && (
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Next Billing Date</label>
                            <div className="mt-1 text-base text-gray-900 dark:text-gray-100">
                                {new Date(organization.subscription_ends_at).toLocaleDateString()}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Pricing Plans */}
            {needsUpgrade && (
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Upgrade Your Plan</h2>

                    <div className="grid gap-6 md:grid-cols-2">
                        {/* Starter Plan */}
                        <div className="rounded-xl border-2 border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Starter</h3>
                            <div className="mt-4 flex items-baseline">
                                <span className="text-4xl font-extrabold text-gray-900 dark:text-white">$29</span>
                                <span className="ml-1 text-gray-500 dark:text-gray-400">/month</span>
                            </div>
                            <ul className="mt-6 space-y-3">
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Up to 10 audits/month</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">5 team members</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Basic integrations</span>
                                </li>
                                <li className="flex items-start">
                                    <X className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-400 line-through">Advanced analytics</span>
                                </li>
                            </ul>
                            <Button
                                className="w-full mt-6"
                                onClick={() => handleUpgrade('price_starter')}
                            >
                                Upgrade to Starter
                            </Button>
                        </div>

                        {/* Pro Plan */}
                        <div className="rounded-xl border-2 border-indigo-600 bg-white p-6 shadow-lg dark:bg-gray-800 relative">
                            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 px-3 py-1 bg-indigo-600 text-white text-xs font-semibold rounded-full">
                                RECOMMENDED
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Pro</h3>
                            <div className="mt-4 flex items-baseline">
                                <span className="text-4xl font-extrabold text-gray-900 dark:text-white">$99</span>
                                <span className="ml-1 text-gray-500 dark:text-gray-400">/month</span>
                            </div>
                            <ul className="mt-6 space-y-3">
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Unlimited audits</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Unlimited team members</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">All integrations</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Advanced analytics</span>
                                </li>
                                <li className="flex items-start">
                                    <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                                    <span className="text-gray-700 dark:text-gray-300">Priority support</span>
                                </li>
                            </ul>
                            <Button
                                className="w-full mt-6"
                                onClick={() => handleUpgrade('price_pro')}
                            >
                                Upgrade to Pro
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {isActive && (
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Manage Subscription</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                        To cancel or modify your subscription, please contact support.
                    </p>
                    <Button variant="outline">Contact Support</Button>
                </div>
            )}
        </div>
    );
}
