import { useState, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { Button } from '../components/ui/Button';
import { Loader2, Mail, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';

export function EmailVerification() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const email = searchParams.get('email') || '';

    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [resendCountdown, setResendCountdown] = useState(60);
    const [canResend, setCanResend] = useState(false);

    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

    // Countdown timer for resend
    useEffect(() => {
        if (resendCountdown > 0) {
            const timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000);
            return () => clearTimeout(timer);
        } else {
            setCanResend(true);
        }
    }, [resendCountdown]);

    // Redirect if no email
    useEffect(() => {
        if (!email) {
            navigate('/register');
        }
    }, [email, navigate]);

    const verifyMutation = useMutation({
        mutationFn: (code: string) => authApi.verifyEmail(email, code),
        onSuccess: (data) => {
            setSuccess(true);
            setError('');

            // Store tokens
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);

            // Redirect to dashboard after 1.5 seconds
            setTimeout(() => {
                navigate('/onboarding');
            }, 1500);
        },
        onError: (err: any) => {
            const errorData = err?.response?.data;
            if (errorData?.attempts_remaining !== undefined) {
                setError(`Invalid code. ${errorData.attempts_remaining} attempts remaining.`);
            } else if (errorData?.error) {
                setError(errorData.error);
            } else {
                setError('Verification failed. Please try again.');
            }
            // Clear OTP on error
            setOtp(['', '', '', '', '', '']);
            inputRefs.current[0]?.focus();
        }
    });

    const resendMutation = useMutation({
        mutationFn: () => authApi.resendOTP(email),
        onSuccess: () => {
            setError('');
            setResendCountdown(60);
            setCanResend(false);
            setOtp(['', '', '', '', '', '']);
            inputRefs.current[0]?.focus();
        },
        onError: (err: any) => {
            setError(err?.response?.data?.error || 'Failed to resend code');
        }
    });

    const handleChange = (index: number, value: string) => {
        // Only allow digits
        if (value && !/^\d$/.test(value)) return;

        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);
        setError('');

        // Auto-focus next input
        if (value && index < 5) {
            inputRefs.current[index + 1]?.focus();
        }

        // Auto-submit when all 6 digits are entered
        if (value && index === 5 && newOtp.every(digit => digit !== '')) {
            const code = newOtp.join('');
            verifyMutation.mutate(code);
        }
    };

    const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            // Move to previous input on backspace if current is empty
            inputRefs.current[index - 1]?.focus();
        } else if (e.key === 'ArrowLeft' && index > 0) {
            inputRefs.current[index - 1]?.focus();
        } else if (e.key === 'ArrowRight' && index < 5) {
            inputRefs.current[index + 1]?.focus();
        }
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
        const newOtp = [...otp];

        for (let i = 0; i < pastedData.length; i++) {
            newOtp[i] = pastedData[i];
        }

        setOtp(newOtp);

        // Focus last filled input or submit if complete
        if (pastedData.length === 6) {
            const code = newOtp.join('');
            verifyMutation.mutate(code);
        } else {
            inputRefs.current[pastedData.length]?.focus();
        }
    };

    const handleResend = () => {
        if (canResend) {
            resendMutation.mutate();
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-indigo-950 px-4">
            <div className="max-w-md w-full">
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 border border-gray-200 dark:border-gray-700">
                    {/* Back button */}
                    <button
                        onClick={() => navigate('/register')}
                        className="flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 mb-6 group"
                    >
                        <ArrowLeft className="h-4 w-4 mr-2 group-hover:-translate-x-1 transition-transform" />
                        Back to registration
                    </button>

                    {/* Header */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full mb-4">
                            <Mail className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                            Verify Your Email
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            We've sent a 6-digit code to<br />
                            <span className="font-semibold text-gray-900 dark:text-gray-100">{email}</span>
                        </p>
                    </div>

                    {/* Success State */}
                    {success && (
                        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                            <div className="flex items-center">
                                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mr-3" />
                                <div>
                                    <p className="text-sm font-medium text-green-800 dark:text-green-200">
                                        Email verified successfully!
                                    </p>
                                    <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">
                                        Redirecting you to your dashboard...
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Error State */}
                    {error && !success && (
                        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <div className="flex items-start">
                                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mr-3 flex-shrink-0 mt-0.5" />
                                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* OTP Input */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 text-center">
                            Enter verification code
                        </label>
                        <div className="flex gap-2 justify-center" onPaste={handlePaste}>
                            {otp.map((digit, index) => (
                                <input
                                    key={index}
                                    ref={(el) => (inputRefs.current[index] = el)}
                                    type="text"
                                    inputMode="numeric"
                                    maxLength={1}
                                    value={digit}
                                    onChange={(e) => handleChange(index, e.target.value)}
                                    onKeyDown={(e) => handleKeyDown(index, e)}
                                    disabled={verifyMutation.isPending || success}
                                    className={`w-12 h-14 text-center text-2xl font-bold rounded-lg border-2 transition-all
                                        ${digit ? 'border-indigo-600 dark:border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20' : 'border-gray-300 dark:border-gray-600'}
                                        focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500 dark:focus:border-indigo-400
                                        bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                    `}
                                    autoFocus={index === 0}
                                />
                            ))}
                        </div>
                    </div>

                    {/* Loading state */}
                    {verifyMutation.isPending && (
                        <div className="flex items-center justify-center mb-6 text-indigo-600 dark:text-indigo-400">
                            <Loader2 className="animate-spin h-5 w-5 mr-2" />
                            <span className="text-sm">Verifying...</span>
                        </div>
                    )}

                    {/* Resend Code */}
                    <div className="text-center">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                            Didn't receive the code?
                        </p>
                        {canResend ? (
                            <button
                                onClick={handleResend}
                                disabled={resendMutation.isPending}
                                className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 disabled:opacity-50"
                            >
                                {resendMutation.isPending ? (
                                    <>
                                        <Loader2 className="inline-block animate-spin h-4 w-4 mr-1" />
                                        Sending...
                                    </>
                                ) : (
                                    'Resend code'
                                )}
                            </button>
                        ) : (
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                Resend available in {resendCountdown}s
                            </span>
                        )}
                    </div>

                    {/* Info box */}
                    <div className="mt-6 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <p className="text-xs text-gray-600 dark:text-gray-400 text-center">
                            🔒 This code will expire in 10 minutes.<br />
                            Check your spam folder if you don't see the email.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
