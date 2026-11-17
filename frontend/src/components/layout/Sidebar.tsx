'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Users,
  Network,
  RefreshCw,
  Webhook,
  Cpu,
  ShieldAlert,
  Bot,
  FileText,
  FileCheck2,
  Settings,
  ShieldCheck
} from 'lucide-react';
import { getStoredUser } from '@/lib/auth';

const NAV_ITEMS = [
  { name: 'Executive Overview', href: '/', icon: Activity },
  { name: 'Patient Records', href: '/patients', icon: Users },
  { name: 'Healthcare Integrations', href: '/integrations', icon: Network },
  { name: 'Data Synchronization', href: '/sync', icon: RefreshCw },
  { name: 'Webhook Events', href: '/webhooks', icon: Webhook },
  { name: 'AI Field Mapping', href: '/ai/mapping', icon: Cpu },
  { name: 'AI Data Quality', href: '/ai/quality', icon: ShieldAlert },
  { name: 'RAG Clinical Assistant', href: '/rag', icon: Bot },
  { name: 'Knowledge Base', href: '/documents', icon: FileText },
  { name: 'HIPAA Audit Trail', href: '/logs', icon: FileCheck2 },
  { name: 'Settings & Vault', href: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const user = getStoredUser();

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 border-r border-slate-800">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-slate-950 font-black shadow-md shadow-teal-500/20">
          <Activity className="w-5 h-5 text-slate-950" />
        </div>
        <div>
          <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-1.5">
            MediSync <span className="text-teal-400 font-extrabold text-xs px-1.5 py-0.5 rounded bg-teal-950/60 border border-teal-800/60">AI</span>
          </h1>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Healthcare Data & RAG</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Clinical Operations
        </div>
        {NAV_ITEMS.slice(0, 5).map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-teal-500/15 text-teal-400 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-teal-400' : 'text-slate-400'}`} />
              <span>{item.name}</span>
            </Link>
          );
        })}

        <div className="pt-4 px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          AI & Knowledge Base
        </div>
        {NAV_ITEMS.slice(5, 9).map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-teal-500/15 text-teal-400 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-teal-400' : 'text-slate-400'}`} />
              <span>{item.name}</span>
            </Link>
          );
        })}

        <div className="pt-4 px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Security & Admin
        </div>
        {NAV_ITEMS.slice(9).map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-teal-500/15 text-teal-400 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-teal-400' : 'text-slate-400'}`} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Status Bar */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center gap-3 px-2 py-1.5 rounded-lg bg-slate-800/40 border border-slate-800">
          <div className="w-7 h-7 rounded-full bg-teal-800/60 text-teal-300 flex items-center justify-center font-bold text-xs border border-teal-600/40">
            {user.email.slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-200 truncate">{user.email}</p>
            <div className="flex items-center gap-1 text-[10px] text-teal-400">
              <ShieldCheck className="w-3 h-3" />
              <span>{user.role}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
