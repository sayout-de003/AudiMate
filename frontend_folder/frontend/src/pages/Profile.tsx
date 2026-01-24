import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { Button } from '../components/ui/Button';
import { Loader2, Save, User, Lock } from 'lucide-react';

export function Profile() {
    const queryClient = useQueryClient();
    const [isEditingProfile, setIsEditingProfile] = useState(false);
    const [isChangingPassword, setIsChangingPassword] = useState(false);

    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    const { data: user, isLoading } = useQuery({
        queryKey: ['me'],
        queryFn: authApi.getMe
    });

    // Set initial values when user data loads
    useEffect(() => {
        if (user && !firstName && !lastName) {
            setFirstName(user.first_name || '');
            setLastName(user.last_name || '');
        }
    }, [user, firstName, lastName]);

    const updateProfileMutation = useMutation({
        mutationFn: (data: { first_name: string; last_name: string }) => authApi.updateProfile(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['me'] });
            setIsEditingProfile(false);
        }
    });

    const changePasswordMutation = useMutation({
        mutationFn: (data: { oldPassword: string; newPassword: string }) =>
            authApi.changePassword(data.oldPassword, data.newPassword),
        onSuccess: () => {
            setIsChangingPassword(false);
            setOldPassword('');
            setNewPassword('');
            setConfirmPassword('');
        }
    });

    const handleUpdateProfile = (e: React.FormEvent) => {
        e.preventDefault();
        updateProfileMutation.mutate({ first_name: firstName, last_name: lastName });
    };

    const handleChangePassword = (e: React.FormEvent) => {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            alert("Passwords don't match");
            return;
        }
        changePasswordMutation.mutate({ oldPassword, newPassword });
    };

    if (isLoading) {
        return (
            <div className="p-12 flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Profile</h1>
                <p className="mt-2 text-gray-500 dark:text-gray-400">Manage your personal information and security settings.</p>
            </div>

            {/* Profile Information */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center">
                        <User className="mr-2 h-5 w-5" />
                        Personal Information
                    </h2>
                    {!isEditingProfile && (
                        <Button size="sm" variant="outline" onClick={() => setIsEditingProfile(true)}>
                            Edit
                        </Button>
                    )}
                </div>

                <form onSubmit={handleUpdateProfile} className="space-y-4">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                First Name
                            </label>
                            {isEditingProfile ? (
                                <input
                                    type="text"
                                    value={firstName}
                                    onChange={(e) => setFirstName(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                                />
                            ) : (
                                <div className="text-base text-gray-900 dark:text-gray-100">{user?.first_name}</div>
                            )}
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Last Name
                            </label>
                            {isEditingProfile ? (
                                <input
                                    type="text"
                                    value={lastName}
                                    onChange={(e) => setLastName(e.target.value)}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                                />
                            ) : (
                                <div className="text-base text-gray-900 dark:text-gray-100">{user?.last_name}</div>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Email
                        </label>
                        <div className="text-base text-gray-900 dark:text-gray-100">{user?.email}</div>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Email cannot be changed</p>
                    </div>

                    {isEditingProfile && (
                        <div className="flex items-center space-x-2 pt-4">
                            <Button type="submit" size="sm" disabled={updateProfileMutation.isPending}>
                                {updateProfileMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                ) : (
                                    <><Save className="mr-2 h-4 w-4" /> Save Changes</>
                                )}
                            </Button>
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                    setIsEditingProfile(false);
                                    setFirstName(user?.first_name || '');
                                    setLastName(user?.last_name || '');
                                }}
                            >
                                Cancel
                            </Button>
                            {updateProfileMutation.isError && (
                                <span className="text-sm text-red-600 dark:text-red-400">Failed to update profile</span>
                            )}
                        </div>
                    )}
                </form>
            </div>

            {/* Password Change */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center">
                        <Lock className="mr-2 h-5 w-5" />
                        Change Password
                    </h2>
                    {!isChangingPassword && (
                        <Button size="sm" variant="outline" onClick={() => setIsChangingPassword(true)}>
                            Change Password
                        </Button>
                    )}
                </div>

                {isChangingPassword ? (
                    <form onSubmit={handleChangePassword} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Current Password
                            </label>
                            <input
                                type="password"
                                value={oldPassword}
                                onChange={(e) => setOldPassword(e.target.value)}
                                required
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                New Password
                            </label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                required
                                minLength={8}
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                Confirm New Password
                            </label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                minLength={8}
                                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>

                        <div className="flex items-center space-x-2 pt-4">
                            <Button type="submit" size="sm" disabled={changePasswordMutation.isPending}>
                                {changePasswordMutation.isPending ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Changing...</>
                                ) : (
                                    'Change Password'
                                )}
                            </Button>
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                    setIsChangingPassword(false);
                                    setOldPassword('');
                                    setNewPassword('');
                                    setConfirmPassword('');
                                }}
                            >
                                Cancel
                            </Button>
                            {changePasswordMutation.isError && (
                                <span className="text-sm text-red-600 dark:text-red-400">Failed to change password</span>
                            )}
                            {changePasswordMutation.isSuccess && (
                                <span className="text-sm text-green-600 dark:text-green-400">Password changed successfully</span>
                            )}
                        </div>
                    </form>
                ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Keep your account secure by using a strong password.
                    </p>
                )}
            </div>
        </div>
    );
}
