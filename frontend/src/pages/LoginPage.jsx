import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Target, Mail, Lock, ArrowRight, Loader2, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const { signIn, signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (isSignUp) {
        await signUp(email, password);
        setSuccess('Account created! Check your email to confirm, then sign in.');
        setIsSignUp(false);
      } else {
        await signIn(email, password);
        navigate('/today');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-stock-green/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-12 h-12 bg-gradient-to-br from-primary to-primary-hover rounded-xl flex items-center justify-center shadow-lg shadow-primary/25">
            <Target size={28} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-wide">Alphahubiq</h1>
        </div>

        {/* Card */}
        <div className="bg-dark-card/80 backdrop-blur-xl border border-dark-border rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-white mb-1">
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-text-muted text-sm mb-6">
            {isSignUp ? 'Join Alphahubiq to track your portfolio' : 'Sign in to your account'}
          </p>

          {error && (
            <div className="mb-4 p-3 bg-stock-red/10 border border-stock-red/30 rounded-lg text-stock-red text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 bg-stock-green/10 border border-stock-green/30 rounded-lg text-stock-green text-sm">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-text-secondary text-sm font-medium mb-1.5">Email</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full bg-dark-bg border border-dark-border text-white text-sm rounded-xl pl-10 pr-4 py-3 focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none placeholder-text-muted"
                />
              </div>
            </div>

            <div>
              <label className="block text-text-secondary text-sm font-medium mb-1.5">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className="w-full bg-dark-bg border border-dark-border text-white text-sm rounded-xl pl-10 pr-12 py-3 focus:ring-2 focus:ring-primary focus:border-primary transition-all outline-none placeholder-text-muted"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-primary to-primary-hover text-white font-semibold py-3 rounded-xl hover:shadow-lg hover:shadow-primary/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <>
                  {isSignUp ? 'Sign Up' : 'Sign In'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => { setIsSignUp(!isSignUp); setError(''); setSuccess(''); }}
              className="text-text-muted text-sm hover:text-primary transition-colors"
            >
              {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>

        <p className="text-text-muted text-xs text-center mt-6">
          © {new Date().getFullYear()} Alphahubiq. AI-Powered Stock Analytics.
        </p>
      </div>
    </div>
  );
}
