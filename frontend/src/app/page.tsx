'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Network,
  RefreshCw,
  FileText,
  ShieldAlert,
  ArrowUpRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Bot,
  Cpu
} from 'lucide-react';
import { MetricCard } from '@/components/ui/MetricCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { api } from '@/lib/api';
import { SyncJob, SyncStatistics, APIIntegration, ClinicalAnomaly } from '@/types';
import { MOCK_QUALITY_REPORT } from '@/lib/mockData';

export default function DashboardPage() {
  const [stats, setStats] = useState<SyncStatistics | null>(null);
  const [recentJobs, setRecentJobs] = useState<SyncJob[]>([]);
  const [integrations, setIntegrations] = useState<APIIntegration[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, jobsData, intData] = await Promise.all([
          api.sync.getStatistics(),
          api.sync.listJobs(),
          api.integrations.list()
        ]);
        setStats(statsData);
        setRecentJobs(jobsData.items.slice(0, 5));
        setIntegrations(intData);
      } catch (e) {
        console.error('Failed to load dashboard data:', e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 rounded-2xl p-6 text-white shadow-sm border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold uppercase tracking-wider mb-2 border border-teal-500/30">
            System Operational • HL7 FHIR R4 Ready
          </span>
          <h1 className="text-2xl font-bold tracking-tight">MediSync AI Platform Overview</h1>
          <p className="mt-1 text-slate-300 text-xs max-w-2xl leading-relaxed">
            Enterprise orchestration engine unifying heterogeneous clinical EHR streams into validated FHIR R4 resources,
            powering Scikit-learn anomaly detection and grounded retrieval-augmented clinical assistance.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/rag"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-500 text-slate-950 font-semibold text-xs hover:bg-teal-400 transition-colors shadow-sm"
          >
            <Bot className="w-4 h-4" />
            <span>Ask Clinical RAG</span>
          </Link>
          <Link
            href="/ai/mapping"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 text-slate-200 font-semibold text-xs hover:bg-slate-700 transition-colors border border-slate-700"
          >
            <Cpu className="w-4 h-4" />
            <span>Map New Schema</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Clinical Records Ingested"
          value={stats?.total_records_ingested?.toLocaleString() || '12,450'}
          subtitle="Persisted in PostgreSQL + pgvector"
          icon={<Users className="w-5 h-5 text-teal-600" />}
          trend={{ value: '+8.4%', isPositive: true }}
        />
        <MetricCard
          title="ETL Sync Success Rate"
          value={`${stats?.success_rate_percentage || 97.3}%`}
          subtitle="Asynchronous Celery worker pool"
          icon={<RefreshCw className="w-5 h-5 text-emerald-600" />}
          trend={{ value: '+1.2%', isPositive: true }}
        />
        <MetricCard
          title="Active API Integrations"
          value={integrations.length || 3}
          subtitle="Epic, Cerner &amp; Proprietary REST"
          icon={<Network className="w-5 h-5 text-sky-600" />}
        />
        <MetricCard
          title="Mean Sync Latency"
          value={`${stats?.average_latency_ms || 1180} ms`}
          subtitle="Transformation &amp; LOINC mapping"
          icon={<Clock className="w-5 h-5 text-indigo-600" />}
          trend={{ value: '-120ms', isPositive: true }}
        />
      </div>

      {/* Two-Column Middle Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Synchronization Jobs (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Recent Synchronization Activity</h3>
              <p className="text-xs text-slate-500">Live Celery asynchronous ETL jobs and batch loads</p>
            </div>
            <Link
              href="/sync"
              className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
            >
              <span>View all jobs</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="mt-4 divide-y divide-slate-100">
            {recentJobs.map((job) => (
              <div key={job.id} className="py-3 flex items-center justify-between hover:bg-slate-50/50 px-2 rounded-lg transition-colors">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-800">
                      {job.integration_name || 'Healthcare Integration'}
                    </span>
                    <StatusBadge status={job.status} size="sm" />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    ID: {job.id} • Processed: <span className="font-medium text-slate-600">{job.records_transformed} records</span> • Duration: {job.execution_duration_ms}ms
                  </p>
                </div>
                <div className="text-right text-[11px] text-slate-400">
                  {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Anomaly & Quality Spotlight (1 Col) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-rose-50 text-rose-600">
                  <ShieldAlert className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">AI Quality Inspection</h3>
              </div>
              <StatusBadge status="HIGH RISK" size="sm" />
            </div>

            <div className="mt-4 space-y-3">
              <div className="p-3 rounded-lg bg-rose-50/60 border border-rose-200/60 text-xs">
                <div className="flex items-center justify-between font-semibold text-rose-900">
                  <span>Systolic Outlier Flagged</span>
                  <span className="text-[10px] bg-rose-200/70 text-rose-800 px-1.5 py-0.5 rounded">IsolationForest</span>
                </div>
                <p className="mt-1 text-slate-600 text-[11px] leading-relaxed">
                  Observation reading <strong>188 mmHg</strong> detected on Patient MRN-100201 exceeding safe physiological boundaries.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                <span className="text-[11px] font-semibold text-slate-700">Missing Mandatory FHIR Fields</span>
                <p className="mt-1 text-slate-500 text-[11px]">
                  2 vendor records lack <code>effectiveDateTime</code> attribute.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-100">
            <Link
              href="/ai/quality"
              className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition-colors"
            >
              <span>Inspect Anomaly Details</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Connected Integrations Card Grid */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Active Healthcare EHR Connectors</h3>
            <p className="text-xs text-slate-500">Live OAuth2, Bearer and API Key credential status</p>
          </div>
          <Link
            href="/integrations"
            className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
          >
            <span>Manage Integrations</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {integrations.map((intg) => (
            <div key={intg.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors space-y-2.5">
              <div className="flex items-center justify-between">
                <StatusBadge status={intg.integration_type} size="sm" />
                <span className="w-2 h-2 rounded-full bg-emerald-500" title="Connection Active" />
              </div>
              <h4 className="text-xs font-bold text-slate-900">{intg.name}</h4>
              <p className="text-[11px] text-slate-500 font-mono truncate">{intg.base_url}</p>
              <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-400">
                <span>Sync every {intg.sync_frequency_minutes}m</span>
                <span className="text-teal-600 font-semibold">{intg.auth_type}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
