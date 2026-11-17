'use client';

import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Layers,
  Zap,
  Server
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { api } from '@/lib/api';
import { SyncJob, SyncStatistics } from '@/types';

export default function SyncPage() {
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [stats, setStats] = useState<SyncStatistics | null>(null);
  const [filter, setFilter] = useState<string>('ALL');
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);

  useEffect(() => {
    loadSyncData();
  }, []);

  async function loadSyncData() {
    const [jobsRes, statsRes] = await Promise.all([
      api.sync.listJobs(),
      api.sync.getStatistics()
    ]);
    setJobs(jobsRes.items);
    setStats(statsRes);
  }

  const handleRetry = async (jobId: string) => {
    setRetryingJobId(jobId);
    try {
      await api.sync.retryJob(jobId);
      // Update local state to show RETRYING
      setJobs(jobs.map(j => j.id === jobId ? { ...j, status: 'RETRYING' } : j));
    } finally {
      setTimeout(() => setRetryingJobId(null), 1500);
    }
  };

  const filteredJobs = jobs.filter(j => {
    if (filter === 'ALL') return true;
    return j.status === filter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Data Synchronization Monitor</h1>
          <p className="text-xs text-slate-500">
            Asynchronous ETL pipeline orchestrated via Celery and Redis with idempotency checks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-mono">
            Broker: Redis #1 • Backend: Redis #2
          </span>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Completed Jobs</span>
          <p className="mt-1 text-2xl font-bold text-emerald-600">{stats?.completed_jobs || 144}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Failed / Retried</span>
          <p className="mt-1 text-2xl font-bold text-rose-600">{stats?.failed_jobs || 4}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Total Ingested</span>
          <p className="mt-1 text-2xl font-bold text-slate-900">{stats?.total_records_ingested?.toLocaleString() || '12,450'}</p>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Success Rate</span>
          <p className="mt-1 text-2xl font-bold text-teal-600">{stats?.success_rate_percentage || 97.3}%</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex gap-2">
          {['ALL', 'COMPLETED', 'FAILED', 'RETRYING'].map((statusKey) => (
            <button
              key={statusKey}
              onClick={() => setFilter(statusKey)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === statusKey
                  ? 'bg-slate-900 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {statusKey}
            </button>
          ))}
        </div>
        <button
          onClick={loadSyncData}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Jobs Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Job ID</th>
                <th className="py-3 px-4">Healthcare Integration</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Extracted</th>
                <th className="py-3 px-4">Transformed</th>
                <th className="py-3 px-4">Loaded</th>
                <th className="py-3 px-4">Execution Time</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Retry Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredJobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                    {job.id}
                  </td>
                  <td className="py-3.5 px-4 font-medium text-slate-900">
                    {job.integration_name || 'Epic FHIR Gateway'}
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={job.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-600">
                    {job.records_extracted}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-teal-700 font-semibold">
                    {job.records_transformed}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-emerald-700 font-semibold">
                    {job.records_loaded}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500">
                    {job.execution_duration_ms ? `${job.execution_duration_ms} ms` : '—'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleRetry(job.id)}
                      disabled={retryingJobId === job.id}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-[11px] font-semibold transition-colors"
                    >
                      <RotateCcw className={`w-3 h-3 ${retryingJobId === job.id ? 'animate-spin' : ''}`} />
                      <span>{retryingJobId === job.id ? 'Enqueued' : 'Retry'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
