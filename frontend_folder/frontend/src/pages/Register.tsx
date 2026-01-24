import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { authApi } from '../api/auth';
import { useNavigate, Link } from 'react-router-dom';
import { Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { useAuth } from '../context/AuthContext';

const registerSchema = z.object({
    first_name: z.string().min(1, 'First name is required'),
    last_name: z.string().min(1, 'Last name is required'),
    email: z.string().email('Please enter a valid email'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
});

type RegisterForm = z.infer<typeof registerSchema>;

export function Register() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [error, setError] = useState<string | null>(null);

    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
        resolver: zodResolver(registerSchema),
    });

    const onSubmit = async (data: RegisterForm) => {
        setError(null);
        try {
            const response = await authApi.register({
                email: data.email,
                password: data.password,
                password_confirm: data.confirm_password,
                first_name: data.first_name,
                last_name: data.last_name
            });

            // Registration successful - redirect to email verification
            console.log('Registration successful, redirecting to email verification');
            navigate(`/verify-email?email=${encodeURIComponent(data.email)}`);
            return;  // Early return after navigation
        } catch (err: any) {
            console.error('Registration error:', err);
            console.error('Error response:', err.response?.data);

            // Safely handle error object logic
            if (err.response?.data) {
                const errorData = err.response.data;

                // Helper to extract string message from error data which might be array or string
                const getErrorMsg = (fieldError: any): string => {
                    if (Array.isArray(fieldError)) {
                        // Join multiple error messages
                        return fieldError.join('. ');
                    }
                    if (typeof fieldError === 'string') return fieldError;
                    if (typeof fieldError === 'object' && fieldError !== null) {
                        // Handle nested error objects
                        const messages = Object.values(fieldError).flat();
                        return messages.join('. ');
                    }
                    return 'Invalid field error';
                };

                // Check for custom exception handler format
                if (errorData.detail) {
                    if (typeof errorData.detail === 'object' && errorData.detail !== null) {
                        // Check for field-specific errors in detail
                        if (errorData.detail.password) {
                            setError(`Password: ${getErrorMsg(errorData.detail.password)}`);
                        } else if (errorData.detail.email) {
                            setError(`Email: ${getErrorMsg(errorData.detail.email)}`);
                        } else if (errorData.detail.password_confirm) {
                            setError(`Confirm Password: ${getErrorMsg(errorData.detail.password_confirm)}`);
                        } else if (errorData.detail.first_name) {
                            setError(`First Name: ${getErrorMsg(errorData.detail.first_name)}`);
                        } else if (errorData.detail.last_name) {
                            setError(`Last Name: ${getErrorMsg(errorData.detail.last_name)}`);
                        } else {
                            // Try to find any field error
                            const keys = Object.keys(errorData.detail);
                            if (keys.length > 0) {
                                const firstKey = keys[0];
                                setError(`${firstKey}: ${getErrorMsg(errorData.detail[firstKey])}`);
                            } else {
                                setError('Registration failed. Please check your inputs.');
                            }
                        }
                    } else {
                        setError(String(errorData.detail));
                    }
                } else if (errorData.email) {
                    setError(`Email: ${getErrorMsg(errorData.email)}`);
                } else if (errorData.password) {
                    setError(`Password: ${getErrorMsg(errorData.password)}`);
                } else if (errorData.password_confirm) {
                    setError(`Confirm Password: ${getErrorMsg(errorData.password_confirm)}`);
                } else if (errorData.first_name) {
                    setError(`First Name: ${getErrorMsg(errorData.first_name)}`);
                } else if (errorData.last_name) {
                    setError(`Last Name: ${getErrorMsg(errorData.last_name)}`);
                } else if (errorData.non_field_errors) {
                    setError(getErrorMsg(errorData.non_field_errors));
                } else if (errorData.message) {
                    setError(errorData.message);
                } else {
                    // Fallback: Show all errors if available
                    const allErrors: string[] = [];
                    Object.keys(errorData).forEach(key => {
                        const msg = getErrorMsg(errorData[key]);
                        if (msg) allErrors.push(`${key}: ${msg}`);
                    });
                    setError(allErrors.length > 0
                        ? allErrors.join(' ')
                        : 'Registration failed. Please check your inputs and try again.');
                }
            } else {
                setError('Failed to register. Please check your connection and try again.');
            }
        }
    }


    return (
        <div className="space-y-6">
            <div className="space-y-2 text-center">
                <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">Create an account</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    Enter your details to get started with AuditEase
                </p>
            </div>

            {error && (
                <div className="p-3 text-sm text-red-500 bg-red-50 dark:bg-red-900/30 dark:text-red-300 rounded-md flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2" />
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="first_name">First Name</Label>
                        <Input
                            id="first_name"
                            placeholder="John"
                            {...register('first_name')}
                            className={errors.first_name ? "border-red-500 focus-visible:ring-red-500" : ""}
                        />
                        {errors.first_name && (
                            <span className="text-xs text-red-500">{errors.first_name.message}</span>
                        )}
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="last_name">Last Name</Label>
                        <Input
                            id="last_name"
                            placeholder="Doe"
                            {...register('last_name')}
                            className={errors.last_name ? "border-red-500 focus-visible:ring-red-500" : ""}
                        />
                        {errors.last_name && (
                            <span className="text-xs text-red-500">{errors.last_name.message}</span>
                        )}
                    </div>
                </div>

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
                    <Label htmlFor="password">Password</Label>
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

                <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirm Password</Label>
                    <Input
                        id="confirm_password"
                        type="password"
                        placeholder="••••••••"
                        {...register('confirm_password')}
                        className={errors.confirm_password ? "border-red-500 focus-visible:ring-red-500" : ""}
                    />
                    {errors.confirm_password && (
                        <span className="text-xs text-red-500">{errors.confirm_password.message}</span>
                    )}
                </div>

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Creating account...
                        </>
                    ) : (
                        'Create account'
                    )}
                </Button>
            </form>

            <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                Already have an account?{' '}
                <Link to="/login" className="font-semibold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                    Sign in
                </Link>
            </div>
        </div>
    );
}
