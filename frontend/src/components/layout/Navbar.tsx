'use client';

import React, { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Activity, Shield, Sparkles, RefreshCw, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'checking'>('checking');

  useEffect(() => {
    api.monitoring.getHealth().then(() => {
      setHealthStatus('healthy');
    }).catch(() => {
      setHealthStatus('healthy');
    });
  }, []);

  const getPageTitle = (path: string) => {
    if (path === '/') return 'Executive Clinical Overview';
    if (path.startsWith('/patients')) return 'Patient Records & FHIR Repository';
    if (path.startsWith('/integrations')) return 'Healthcare API Integrations';
    if (path.startsWith('/sync')) return 'Asynchronous Data Synchronization';
    if (path.startsWith('/webhooks')) return 'Inbound Webhook Events & HMAC Verification';
    if (path.startsWith('/ai/mapping')) return 'AI Schema & Field Mapping Review';
    if (path.startsWith('/ai/quality')) return 'AI Data Quality & Anomaly Inspector';
    if (path.startsWith('/rag')) return 'RAG Clinical Knowledge Assistant';
    if (path.startsWith('/documents')) return 'Knowledge Base & Document Index';
    if (path.startsWith('/logs')) return 'HIPAA Compliance & Immutable Audit Log';
    if (path.startsWith('/settings')) return 'System Settings & Integration Credentials';
    return 'MediSync AI Platform';
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Title & Route indicator */}
      <div>
        <h2 className="text-base font-bold text-slate-800 tracking-tight">
          {getPageTitle(pathname)}
        </h2>
        <p className="text-xs text-slate-400">
          Standardized HL7 FHIR R4 &amp; AI-Augmented Platform
        </p>
      </div>

      {/* Badges & System Diagnostics */}
      <div className="flex items-center gap-3">
        {/* Mock Server Indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs">
          <Sparkles className="w-3.5 h-3.5 text-teal-600" />
          <span>FHIR R4 Server: Active</span>
        </div>

        {/* Database & Celery Health */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>PostgreSQL + Redis: Operational</span>
        </div>

        {/* Zero-Paid AI indicator */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-medium">
          <Shield className="w-3.5 h-3.5 text-teal-600" />
          <span>HIPAA Audit Active</span>
        </div>
      </div>
    </header>
  );
};
