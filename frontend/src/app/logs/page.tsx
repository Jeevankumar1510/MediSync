'use client';

import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  Shield,
  Search,
  Filter,
  Eye,
  Lock,
  Download
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Modal } from '@/components/ui/Modal';
import { JsonViewer } from '@/components/ui/JsonViewer';
import { api } from '@/lib/api';
import { AuditLogEntry } from '@/types';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [filterAction, setFilterAction] = useState('ALL');

  useEffect(() => {
    loadLogs();
  }, []);

  async function loadLogs() {
    const res = await api.monitoring.getAuditLogs();
    setLogs(res.items);
  }

  const handleInspect = (log: AuditLogEntry) => {
    setSelectedLog(log);
    setIsModalOpen(true);
  };

  const filteredLogs = logs.filter(l => {
    if (filterAction === 'ALL') return true;
    return l.action === filterAction;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">HIPAA Compliance &amp; Audit Trail</h1>
          <p className="text-xs text-slate-500">
            Immutable, cryptographically verifiable log of all patient accesses, sync dispatches, and AI inference queries
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-teal-600" />
            <span>Immutable Append-Only Audit</span>
          </span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 font-medium">Filter Action:</span>
          {['ALL', 'RAG_QUERY', 'SYNC_DISPATCH', 'PATIENT_READ', 'WEBHOOK_INGEST'].map(act => (
            <button
              key={act}
              onClick={() => setFilterAction(act)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
                filterAction === act
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {act}
            </button>
          ))}
        </div>
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `medisync_hipaa_audit_${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold self-start sm:self-auto"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Export Audit (JSON)</span>
        </button>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Audit ID</th>
                <th className="py-3 px-4">User / Actor</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Resource Target</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Context</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                    {log.id}
                  </td>
                  <td className="py-3.5 px-4 text-slate-900 font-medium">
                    {log.user_email || 'system@medisync.local'}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="font-mono px-2 py-0.5 rounded bg-teal-50 text-teal-800 font-bold text-[11px] border border-teal-200">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-600">
                    {log.resource_type} {log.resource_id ? `(${log.resource_id})` : ''}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleInspect(log)}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-[11px] font-semibold transition-colors inline-flex items-center gap-1"
                    >
                      <Eye className="w-3 h-3" />
                      <span>Details</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Log Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={`HIPAA Audit Context — ${selectedLog?.id}`}
      >
        {selectedLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">User Principal</span>
                <span className="font-bold text-slate-800">{selectedLog.user_email}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Action Performed</span>
                <span className="font-bold text-teal-800 font-mono">{selectedLog.action}</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-800 mb-1.5">Context &amp; Request Parameters</h4>
              <JsonViewer data={selectedLog.details} title="Audit Record Metadata" maxHeight="max-h-72" />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
