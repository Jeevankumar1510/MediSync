'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Activity, Lock, Mail, ArrowRight, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { setStoredAuth } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@medisync.local');
  const [password, setPassword] = useState('Admin@123456');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.auth.login(email, password);
      setStoredAuth(res.access_token, res.user);
      router.push('/');
    } catch (err: any) {
      setError(err?.message || 'Login failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-400 to-teal-600 mx-auto flex items-center justify-center shadow-lg shadow-teal-500/20">
          <Activity className="w-7 h-7 text-slate-950" />
        </div>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-white">
          Sign in to MediSync AI
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          Intelligent Healthcare Data Integration &amp; RAG Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 py-8 px-6 shadow-xl rounded-2xl sm:px-10 border border-slate-800 space-y-6">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 outline-none focus:border-teal-500 transition-colors"
                  placeholder="admin@medisync.local"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 outline-none focus:border-teal-500 transition-colors"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-teal-500 text-slate-950 font-bold hover:bg-teal-400 transition-colors flex items-center justify-center gap-1.5 shadow-sm mt-2"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Quick Demo Sign In Pills */}
          <div className="pt-4 border-t border-slate-800">
            <p className="text-[11px] font-semibold text-slate-400 mb-2">Preset Demo Credentials:</p>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <button
                type="button"
                onClick={() => {
                  setEmail('admin@medisync.local');
                  setPassword('Admin@123456');
                }}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-left border border-slate-700/60 transition-colors"
              >
                <span className="font-bold block text-teal-400">ADMIN</span>
                <span>admin@medisync.local</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail('analyst@medisync.local');
                  setPassword('Analyst@123456');
                }}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-left border border-slate-700/60 transition-colors"
              >
                <span className="font-bold block text-teal-400">CLINICAL ANALYST</span>
                <span>analyst@medisync.local</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
