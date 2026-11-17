'use client';

import React, { useState } from 'react';
import {
  Settings,
  Shield,
  KeyRound,
  Database,
  Server,
  UserCheck,
  CheckCircle2,
  Lock,
  Layers
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { getStoredUser } from '@/lib/auth';
import { UserRole } from '@/types';

const RBAC_PERMISSIONS: { role: UserRole; label: string; perms: string[] }[] = [
  {
    role: 'ADMIN',
    label: 'Platform Administrator',
    perms: ['Full system access', 'Manage users & roles', 'Configure integrations', 'Trigger ETL sync', 'Manage knowledge base', 'Export HIPAA audit logs']
  },
  {
    role: 'INTEGRATION_ENGINEER',
    label: 'Integration Engineer',
    perms: ['Configure API integrations', 'Manage credentials vault', 'Trigger ETL sync', 'Review AI field mapping', 'Inspect webhooks', 'View diagnostics']
  },
  {
    role: 'CLINICAL_ANALYST',
    label: 'Clinical Analyst',
    perms: ['Read patient demographics', 'Inspect normalized FHIR records', 'Query RAG assistant', 'View data quality anomalies', 'Upload clinical guidelines']
  },
  {
    role: 'VIEWER',
    label: 'Read-Only Viewer',
    perms: ['Read aggregated statistics', 'View operational health', 'Query public knowledge base']
  }
];

export default function SettingsPage() {
  const [user, setUser] = useState(getStoredUser());
  const [savedNotice, setSavedNotice] = useState<string | null>(null);

  const switchRole = (newRole: UserRole) => {
    const updated = { ...user, role: newRole };
    setUser(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('medisync_user', JSON.stringify(updated));
    }
    setSavedNotice(`Active role switched to '${newRole}'.`);
    setTimeout(() => setSavedNotice(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">System Configuration &amp; Security Vault</h1>
          <p className="text-xs text-slate-500">
            Platform environment settings, cryptographic keys, and Role-Based Access Control (RBAC)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-teal-600" />
            <span>Fernet AES-128 Active</span>
          </span>
        </div>
      </div>

      {savedNotice && (
        <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs flex items-center gap-2 font-medium">
          <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <span>{savedNotice}</span>
        </div>
      )}

      {/* User Profile & Demo Role Switcher */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Active User Profile</h3>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-teal-700 text-teal-100 flex items-center justify-center font-bold text-sm">
              {user.email.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900">{user.email}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <StatusBadge status={user.role} size="sm" />
                <span className="text-[11px] text-slate-400">UUID: {user.id}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Switch Demo Role:</span>
            <select
              value={user.role}
              onChange={(e) => switchRole(e.target.value as UserRole)}
              className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-800 bg-white outline-none focus:border-teal-500"
            >
              <option value="ADMIN">ADMIN</option>
              <option value="INTEGRATION_ENGINEER">INTEGRATION_ENGINEER</option>
              <option value="CLINICAL_ANALYST">CLINICAL_ANALYST</option>
              <option value="VIEWER">VIEWER</option>
            </select>
          </div>
        </div>
      </div>

      {/* System Infrastructure Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
            <Database className="w-4 h-4 text-teal-600" />
            <span>Relational &amp; Vector Store</span>
          </div>
          <p className="text-sm font-semibold text-slate-900">PostgreSQL 16 + pgvector</p>
          <p className="text-[11px] text-slate-500">
            Port 5432 • Dual asyncpg (FastAPI) and psycopg2 (Celery/Alembic) drivers
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
            <Server className="w-4 h-4 text-emerald-600" />
            <span>Message Broker &amp; Backend</span>
          </div>
          <p className="text-sm font-semibold text-slate-900">Redis 7.0 In-Memory</p>
          <p className="text-[11px] text-slate-500">
            Port 6379 • DB #0 Cache • DB #1 Celery Broker • DB #2 Celery Results
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-slate-800 font-bold text-xs">
            <KeyRound className="w-4 h-4 text-amber-600" />
            <span>Cryptographic Vault</span>
          </div>
          <p className="text-sm font-semibold text-slate-900">Fernet AES-128 Encryption</p>
          <p className="text-[11px] text-slate-500">
            Symmetric authenticated encryption securing all external API credentials
          </p>
        </div>
      </div>

      {/* RBAC Matrix */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Role-Based Access Control (RBAC) Entitlements
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {RBAC_PERMISSIONS.map((p) => (
            <div key={p.role} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-900">{p.label}</span>
                <StatusBadge status={p.role} size="sm" />
              </div>
              <ul className="space-y-1 text-slate-600 text-[11px]">
                {p.perms.map((perm, idx) => (
                  <li key={idx} className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 flex-shrink-0" />
                    <span>{perm}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
