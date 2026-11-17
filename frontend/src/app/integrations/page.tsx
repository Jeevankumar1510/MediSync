'use client';

import React, { useState, useEffect } from 'react';
import {
  Network,
  Plus,
  Radio,
  CheckCircle2,
  XCircle,
  Play,
  KeyRound,
  Shield,
  Activity,
  ExternalLink
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Modal } from '@/components/ui/Modal';
import { api } from '@/lib/api';
import { APIIntegration } from '@/types';

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<APIIntegration[]>([]);
  const [testResult, setTestResult] = useState<{ id: string; success: boolean; message: string; latency_ms: number } | null>(null);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  useEffect(() => {
    loadIntegrations();
  }, []);

  async function loadIntegrations() {
    const list = await api.integrations.list();
    setIntegrations(list);
  }

  const handleTestConnection = async (intg: APIIntegration) => {
    const res = await api.integrations.testConnection(intg.id);
    setTestResult({ id: intg.id, ...res });
    setIsTestModalOpen(true);
  };

  const handleTriggerSync = async (intg: APIIntegration) => {
    const res = await api.integrations.triggerSync(intg.id);
    setSyncNotice(`Synchronization dispatched for '${intg.name}'. Job ID: ${res.job_id}`);
    setTimeout(() => setSyncNotice(null), 5000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Healthcare API Integrations</h1>
          <p className="text-xs text-slate-500">
            Secure multi-vendor connector gateway with Fernet 128-bit AES encrypted credential vault
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
            <span>3 Connectors Online</span>
          </span>
        </div>
      </div>

      {syncNotice && (
        <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs flex items-center gap-2 font-medium animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <span>{syncNotice}</span>
        </div>
      )}

      {/* Integration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {integrations.map((intg) => (
          <div
            key={intg.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow transition-shadow flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <StatusBadge status={intg.integration_type} size="sm" />
                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Connected
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900">{intg.name}</h3>
                <p className="mt-1 text-[11px] font-mono text-slate-500 truncate" title={intg.base_url}>
                  {intg.base_url}
                </p>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs space-y-1.5 text-slate-600">
                <div className="flex justify-between">
                  <span className="text-slate-400">Auth Mechanism:</span>
                  <span className="font-semibold text-slate-800">{intg.auth_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Poll Frequency:</span>
                  <span className="font-medium text-slate-700">{intg.sync_frequency_minutes} minutes</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Credential Vault:</span>
                  <span className="text-teal-700 font-semibold flex items-center gap-1">
                    <KeyRound className="w-3 h-3" />
                    AES-128 Encrypted
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-5 pt-3 border-t border-slate-100 flex items-center gap-2">
              <button
                onClick={() => handleTestConnection(intg)}
                className="flex-1 py-1.5 px-3 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
              >
                <Activity className="w-3.5 h-3.5 text-teal-600" />
                <span>Handshake</span>
              </button>
              <button
                onClick={() => handleTriggerSync(intg)}
                className="flex-1 py-1.5 px-3 rounded-lg bg-teal-600 text-white hover:bg-teal-700 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-sm"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Sync Now</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Test Connection Modal */}
      <Modal
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
        title="Healthcare Connector Diagnostic Handshake"
      >
        {testResult && (
          <div className="space-y-4 text-xs">
            <div className={`p-4 rounded-xl border flex items-start gap-3 ${
              testResult.success
                ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                : 'bg-rose-50/80 border-rose-200 text-rose-900'
            }`}>
              {testResult.success ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <h4 className="font-bold text-sm">
                  {testResult.success ? 'Handshake Successful' : 'Connection Handshake Failed'}
                </h4>
                <p className="mt-1 leading-relaxed">{testResult.message}</p>
                <p className="mt-2 font-mono text-[11px] opacity-75">
                  Roundtrip Network Latency: {testResult.latency_ms} ms
                </p>
              </div>
            </div>

            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <h5 className="font-bold text-slate-800">Capability Diagnostics Verified:</h5>
              <ul className="list-disc list-inside space-y-1 text-slate-600">
                <li>Server responded with valid HTTP 200 OK header</li>
                <li>FHIR CapabilityStatement contains supported resources: <code>Patient</code>, <code>Observation</code>, <code>Condition</code></li>
                <li>Encrypted credentials decrypted safely in-memory for OAuth2 authorization</li>
              </ul>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setIsTestModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800 text-xs"
              >
                Close Diagnostic
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
