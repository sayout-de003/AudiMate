import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { orgsApi, type Member } from '../api/orgs';
import { Button } from '../components/ui/Button';
import { Loader2, Plus, Trash2, Save, Building2, AlertCircle } from 'lucide-react';

export function Settings() {
    const queryClient = useQueryClient();
    const [orgName, setOrgName] = useState('');
    const [inviteEmail, setInviteEmail] = useState('');
    const [memberToRemove, setMemberToRemove] = useState<number | null>(null);

    const { data: user, isLoading: userLoading } = useQuery({
        queryKey: ['me'],
        queryFn: authApi.getMe
    });

    const currentOrgId = user?.current_organization || user?.organizations?.[0]?.id;

    const { data: organization, isLoading: orgLoading } = useQuery({
        queryKey: ['organization', currentOrgId],
        queryFn: () => orgsApi.get(currentOrgId!),
        enabled: !!currentOrgId
    });

    const { data: members = [], isLoading: membersLoading } = useQuery({
        queryKey: ['members', currentOrgId],
        queryFn: () => orgsApi.listMembers(currentOrgId!),
        enabled: !!currentOrgId
    });

    const updateOrgMutation = useMutation({
        mutationFn: (name: string) => orgsApi.update(currentOrgId!, { name }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['organization', currentOrgId] });
            queryClient.invalidateQueries({ queryKey: ['me'] });
        }
    });

    const inviteMutation = useMutation({
        mutationFn: (email: string) => orgsApi.inviteMember(currentOrgId!, email),
        onSuccess: () => {
            setInviteEmail('');
            queryClient.invalidateQueries({ queryKey: ['members', currentOrgId] });
        }
    });

    const removeMemberMutation = useMutation({
        mutationFn: (userId: number) => orgsApi.removeMember(currentOrgId!, userId),
        onSuccess: () => {
            setMemberToRemove(null);
            queryClient.invalidateQueries({ queryKey: ['members', currentOrgId] });
        }
    });

    const handleUpdateOrg = (e: React.FormEvent) => {
        e.preventDefault();
        if (orgName.trim() && orgName !== organization?.name) {
            updateOrgMutation.mutate(orgName.trim());
        }
    };

    const handleInvite = (e: React.FormEvent) => {
        e.preventDefault();
        if (inviteEmail.trim()) {
            inviteMutation.mutate(inviteEmail.trim());
        }
    };

    if (userLoading || orgLoading) {
        return (
            <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            </div>
        );
    }

    const isAdmin = organization?.role === 'ADMIN';

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Settings</h1>
                <p className="mt-1 text-gray-500 dark:text-gray-400">Manage your organization and member access.</p>
            </div>

            {/* Organization Profile */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center">
                        <Building2 className="mr-2 h-5 w-5" />
                        Organization Profile
                    </h2>
                </div>

                <form onSubmit={handleUpdateOrg} className="space-y-4">
                    <div className="grid grid-cols-1 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Organization Name</label>
                            {isAdmin ? (
                                <div className="mt-1">
                                    <input
                                        type="text"
                                        value={orgName || organization?.name || ''}
                                        onChange={(e) => setOrgName(e.target.value)}
                                        onFocus={() => setOrgName(organization?.name || '')}
                                        placeholder="Enter organization name"
                                        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                                    />
                                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                        Only admins can change the organization name
                                    </p>
                                </div>
                            ) : (
                                <div className="mt-1 text-base font-medium text-gray-900 dark:text-gray-100">
                                    {organization?.name}
                                </div>
                            )}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Your Role</label>
                            <div className="mt-1 text-base font-medium text-gray-900 dark:text-gray-100">
                                {organization?.role || 'Member'}
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Member Since</label>
                            <div className="mt-1 text-base font-medium text-gray-900 dark:text-gray-100">
                                {organization?.created_at ? new Date(organization.created_at).toLocaleDateString() : '-'}
                            </div>
                        </div>
                    </div>

                    {isAdmin && (
                        <div className="flex items-center space-x-2 pt-2">
                            {orgName && orgName !== organization?.name ? (
                                <>
                                    <Button type="submit" size="sm" disabled={updateOrgMutation.isPending}>
                                        {updateOrgMutation.isPending ? (
                                            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                        ) : (
                                            <><Save className="mr-2 h-4 w-4" /> Save Changes</>
                                        )}
                                    </Button>
                                    <Button 
                                        type="button" 
                                        variant="outline" 
                                        size="sm"
                                        onClick={() => setOrgName(organization?.name || '')}
                                        disabled={updateOrgMutation.isPending}
                                    >
                                        Cancel
                                    </Button>
                                </>
                            ) : (
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Edit the organization name above to save changes
                                </p>
                            )}
                            {updateOrgMutation.isError && (
                                <span className="text-sm text-red-600 dark:text-red-400">Failed to update organization name</span>
                            )}
                            {updateOrgMutation.isSuccess && (
                                <span className="text-sm text-green-600 dark:text-green-400">Organization name updated successfully</span>
                            )}
                        </div>
                    )}
                </form>
            </div>

            {/* Subscription Status */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                        Subscription
                    </h2>
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Plan Status</label>
                            <div className="mt-1 flex items-center space-x-2">
                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${organization?.subscription_status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                                        organization?.subscription_status === 'trial' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' :
                                            organization?.subscription_status === 'past_due' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' :
                                                organization?.subscription_status === 'expired' || organization?.subscription_status === 'canceled' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                                                    'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                                    }`}>
                                    {organization?.subscription_status === 'free' && '🆓 Free Plan'}
                                    {organization?.subscription_status === 'trial' && '⏱️ Trial'}
                                    {organization?.subscription_status === 'active' && '✅ Active'}
                                    {organization?.subscription_status === 'past_due' && '⚠️ Past Due'}
                                    {organization?.subscription_status === 'expired' && '❌ Expired'}
                                    {organization?.subscription_status === 'canceled' && '🚫 Canceled'}
                                </span>
                            </div>
                        </div>
                        {(organization?.subscription_status === 'free' || organization?.subscription_status === 'trial') && (
                            <Button size="sm" onClick={() => window.location.href = '/billing'}>
                                Upgrade Plan
                            </Button>
                        )}
                    </div>

                    {organization?.trial_end_date && organization?.subscription_status === 'trial' && (
                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                            <p className="text-sm text-blue-700 dark:text-blue-300">
                                Trial ends on {new Date(organization.trial_end_date).toLocaleDateString()}
                            </p>
                        </div>
                    )}

                    {organization?.subscription_ends_at && organization?.subscription_status === 'active' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Next Billing Date</label>
                            <div className="mt-1 text-base text-gray-900 dark:text-gray-100">
                                {new Date(organization.subscription_ends_at).toLocaleDateString()}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Team Members */}
            <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">Team Members</h2>
                </div>

                {membersLoading ? (
                    <div className="p-12 flex justify-center">
                        <Loader2 className="animate-spin h-6 w-6 text-indigo-600" />
                    </div>
                ) : members.length > 0 ? (
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {members.map((member: Member) => (
                            <div key={member.id} className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                                <div className="flex items-center space-x-4">
                                    <div className="h-10 w-10 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                                        <span className="text-indigo-600 dark:text-indigo-300 font-medium">
                                            {member.first_name?.[0]}{member.last_name?.[0]}
                                        </span>
                                    </div>
                                    <div>
                                        <div className="font-medium text-gray-900 dark:text-gray-100">
                                            {member.first_name} {member.last_name}
                                        </div>
                                        <div className="text-sm text-gray-500 dark:text-gray-400">{member.email}</div>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <span className="px-3 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                                        {member.role}
                                    </span>
                                    {isAdmin && member.id !== user?.id && (
                                        <button
                                            onClick={() => setMemberToRemove(member.id)}
                                            className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="p-12 text-center">
                        <div className="text-gray-500 dark:text-gray-400">No other members in this organization yet.</div>
                    </div>
                )}

                {isAdmin && (
                    <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/30">
                        <form onSubmit={handleInvite} className="flex space-x-3">
                            <input
                                type="email"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                placeholder="colleague@example.com"
                                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                                disabled={inviteMutation.isPending}
                            />
                            <Button type="submit" size="sm" disabled={!inviteEmail.trim() || inviteMutation.isPending}>
                                {inviteMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Inviting...</>
                                ) : (
                                    <><Plus className="mr-2 h-4 w-4" /> Invite Member</>
                                )}
                            </Button>
                        </form>
                        {inviteMutation.isError && (
                            <p className="mt-2 text-sm text-red-600 dark:text-red-400 flex items-center">
                                <AlertCircle className="mr-1 h-4 w-4" />
                                Failed to send invitation
                            </p>
                        )}
                        {inviteMutation.isSuccess && (
                            <p className="mt-2 text-sm text-green-600 dark:text-green-400">
                                Invitation sent successfully!
                            </p>
                        )}
                    </div>
                )}
            </div>

            {/* Remove Member Confirmation Dialog */}
            {memberToRemove && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4">
                        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">Remove Member</h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            Are you sure you want to remove this member from the organization?
                        </p>
                        <div className="flex space-x-3">
                            <Button
                                variant="outline"
                                onClick={() => setMemberToRemove(null)}
                                className="flex-1"
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={() => removeMemberMutation.mutate(memberToRemove)}
                                disabled={removeMemberMutation.isPending}
                                className="flex-1 bg-red-600 hover:bg-red-700"
                            >
                                {removeMemberMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Removing...</>
                                ) : (
                                    'Remove'
                                )}
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
