import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp';
import { DollarSign, Mail, Lock, Eye, EyeOff, Shield } from 'lucide-react';
import { toast } from 'sonner';

export default function LoginPage() {
  const { login, verifyTOTP, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [requiresTOTP, setRequiresTOTP] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const hasProcessedRef = useRef(false);

  // Check for session_id in hash
  useEffect(() => {
    if (hasProcessedRef.current) return;
    
    const hash = location.hash;
    if (hash.includes('session_id=')) {
      hasProcessedRef.current = true;
      // Auth context will handle this
    }
  }, [location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result.requires_totp) {
        setRequiresTOTP(true);
        setTempToken(result.temp_token);
        toast.info('Enter your 2FA code');
      } else {
        toast.success('Welcome back!');
        navigate(result.setup_completed ? '/dashboard' : '/setup');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTOTPSubmit = async () => {
    if (totpCode.length !== 6) return;
    setLoading(true);
    try {
      const result = await verifyTOTP(totpCode, tempToken);
      toast.success('Welcome back!');
      navigate(result.setup_completed ? '/dashboard' : '/setup');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid code');
      setTotpCode('');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (totpCode.length === 6) {
      handleTOTPSubmit();
    }
  }, [totpCode]);

  return (
    <div className="min-h-screen bg-[#09090b] flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ 
            backgroundImage: 'url(https://images.unsplash.com/photo-1602513531640-f41c6939e38b?w=1200)',
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#09090b] via-[#09090b]/80 to-transparent" />
        <div className="relative z-10 flex flex-col justify-center p-12">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center">
              <DollarSign className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="font-heading font-bold text-2xl text-white">CAD Finance</h1>
              <p className="text-sm text-zinc-400">Business Suite</p>
            </div>
          </div>
          <h2 className="font-heading text-4xl font-bold text-white mb-4">
            Your Financial<br />Command Center
          </h2>
          <p className="text-lg text-zinc-400 max-w-md">
            Track income, manage expenses, and stay on top of your Canadian tax obligations with our comprehensive finance suite.
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-white" />
            </div>
            <span className="font-heading font-bold text-xl text-white">CAD Finance</span>
          </div>

          {!requiresTOTP ? (
            <>
              <h2 className="font-heading text-2xl font-bold text-white mb-2">Welcome back</h2>
              <p className="text-zinc-400 mb-8">Sign in to your account to continue</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="finance-input pl-10"
                      required
                      data-testid="input-email"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="finance-input pl-10 pr-10"
                      required
                      data-testid="input-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full finance-btn-primary"
                  disabled={loading}
                  data-testid="btn-login"
                >
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>
              </form>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-zinc-800"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-[#09090b] text-zinc-500">or continue with</span>
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full border-zinc-700 hover:bg-zinc-800"
                onClick={loginWithGoogle}
                data-testid="btn-google"
              >
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Google
              </Button>

              <p className="text-center text-sm text-zinc-400 mt-6">
                Don't have an account?{' '}
                <Link to="/register" className="text-emerald-400 hover:underline" data-testid="link-register">
                  Create one
                </Link>
              </p>
            </>
          ) : (
            <>
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                  <Shield className="w-8 h-8 text-emerald-400" />
                </div>
                <h2 className="font-heading text-2xl font-bold text-white mb-2">Two-Factor Authentication</h2>
                <p className="text-zinc-400">Enter the 6-digit code from your authenticator app</p>
              </div>

              <div className="flex justify-center mb-6">
                <InputOTP
                  maxLength={6}
                  value={totpCode}
                  onChange={setTotpCode}
                  data-testid="input-totp"
                >
                  <InputOTPGroup className="gap-2">
                    {[0, 1, 2, 3, 4, 5].map((i) => (
                      <InputOTPSlot
                        key={i}
                        index={i}
                        className="w-12 h-14 text-xl bg-zinc-900 border-zinc-700"
                      />
                    ))}
                  </InputOTPGroup>
                </InputOTP>
              </div>

              {loading && (
                <div className="flex justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-emerald-500"></div>
                </div>
              )}

              <Button
                variant="ghost"
                className="w-full mt-4"
                onClick={() => {
                  setRequiresTOTP(false);
                  setTotpCode('');
                  setTempToken('');
                }}
              >
                Back to login
              </Button>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
