import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import { useNavigate, Link } from 'react-router-dom';
import { Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';

const loginSchema = z.object({
    email: z.string().email('Please enter a valid email'),
    password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

export function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const [error, setError] = useState<string | null>(null);

    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginForm) => {
        setError(null);
        try {
            const response = await authApi.login(data);
            if (response.access) {
                login(response.access, response.refresh);
                navigate('/');
            }
        } catch (err: any) {
            console.error(err);
            if (err.response?.data?.non_field_errors) {
                setError(err.response.data.non_field_errors[0]);
            } else if (err.response?.data?.detail) {
                setError(err.response.data.detail);
            } else {
                setError('Failed to login. Please check your credentials.');
            }
        }
    };

    return (
        <div className="space-y-6">
            <div className="space-y-2 text-center">
                <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Welcome back</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    Enter your credentials to access your account
                </p>
            </div>

            {error && (
                <div className="p-3 text-sm text-red-500 bg-red-50 dark:bg-red-900/30 dark:text-red-300 rounded-md flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                        id="email"
                        type="email"
                        placeholder="name@company.com"
                        {...register('email')}
                        className={errors.email ? "border-red-500 focus-visible:ring-red-500" : ""}
                    />
                    {errors.email && (
                        <span className="text-xs text-red-500">{errors.email.message}</span>
                    )}
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <Label htmlFor="password">Password</Label>
                        <Link to="/forgot-password" className="text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                            Forgot password?
                        </Link>
                    </div>
                    <Input
                        id="password"
                        type="password"
                        placeholder="••••••••"
                        {...register('password')}
                        className={errors.password ? "border-red-500 focus-visible:ring-red-500" : ""}
                    />
                    {errors.password && (
                        <span className="text-xs text-red-500">{errors.password.message}</span>
                    )}
                </div>

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Signing in...
                        </>
                    ) : (
                        'Sign in'
                    )}
                </Button>
            </form>

            <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                Don't have an account?{' '}
                <Link to="/register" className="font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                    Sign up
                </Link>
            </div>
        </div>
    );
}
