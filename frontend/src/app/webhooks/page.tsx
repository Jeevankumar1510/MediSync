'use client';

import React, { useState, useEffect } from 'react';
import {
  Webhook,
  ShieldCheck,
  ShieldAlert,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Eye,
  KeyRound
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Modal } from '@/components/ui/Modal';
import { JsonViewer } from '@/components/ui/JsonViewer';
import { api } from '@/lib/api';
import { WebhookEvent } from '@/types';

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookEvent[]>([]);
  const [selectedWebhook, setSelectedWebhook] = useState<WebhookEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [retryNotice, setRetryNotice] = useState<string | null>(null);

  useEffect(() => {
    loadWebhooks();
  }, []);

  async function loadWebhooks() {
    const res = await api.webhooks.list();
    setWebhooks(res.items);
  }

  const handleInspect = (wh: WebhookEvent) => {
    setSelectedWebhook(wh);
    setIsModalOpen(true);
  };

  const handleRetry = async (wh: WebhookEvent) => {
    await api.webhooks.retry(wh.id);
    setRetryNotice(`Webhook event '${wh.event_id}' dispatched to Celery worker queue.`);
    setTimeout(() => setRetryNotice(null), 4000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Inbound Webhook Management</h1>
          <p className="text-xs text-slate-500">
            Real-time HL7 and EHR event ingestion with constant-time HMAC-SHA256 signature verification
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold flex items-center gap-1.5">
            <KeyRound className="w-3.5 h-3.5 text-teal-600" />
            <span>X-MediSync-Signature Enforced</span>
          </span>
        </div>
      </div>

      {retryNotice && (
        <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs flex items-center gap-2 font-medium">
          <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <span>{retryNotice}</span>
        </div>
      )}

      {/* Webhooks Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Event ID</th>
                <th className="py-3 px-4">Origin / Source</th>
                <th className="py-3 px-4">Event Classification</th>
                <th className="py-3 px-4">Processing Status</th>
                <th className="py-3 px-4">HMAC Signature</th>
                <th className="py-3 px-4">Retries</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {webhooks.map((wh) => (
                <tr key={wh.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                    {wh.event_id}
                  </td>
                  <td className="py-3.5 px-4 font-medium text-slate-900">
                    {wh.source}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-[11px] text-teal-800">
                    {wh.event_type}
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={wh.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-4">
                    {wh.signature_verified ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Verified</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                        <span>Mismatch</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500 font-mono">
                    {wh.retry_count}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                    {new Date(wh.created_at).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4 text-right space-x-1.5">
                    <button
                      onClick={() => handleInspect(wh)}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-[11px] font-semibold transition-colors"
                    >
                      Inspect
                    </button>
                    {wh.status === 'FAILED' && (
                      <button
                        onClick={() => handleRetry(wh)}
                        className="px-2.5 py-1 rounded-lg bg-teal-50 text-teal-700 hover:bg-teal-100 text-[11px] font-semibold transition-colors"
                      >
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Webhook Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={`Webhook Inspection — ${selectedWebhook?.event_id}`}
        maxWidth="max-w-3xl"
      >
        {selectedWebhook && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Source</span>
                <span className="font-bold text-slate-800">{selectedWebhook.source}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Event Type</span>
                <span className="font-bold text-slate-800">{selectedWebhook.event_type}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">HMAC Status</span>
                <span className={`font-semibold ${selectedWebhook.signature_verified ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {selectedWebhook.signature_verified ? 'Verified Valid' : 'Signature Rejected'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Status</span>
                <StatusBadge status={selectedWebhook.status} size="sm" />
              </div>
            </div>

            {selectedWebhook.error_message && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                <strong>Error: </strong> {selectedWebhook.error_message}
              </div>
            )}

            <div>
              <h4 className="text-xs font-bold text-slate-800 mb-1.5">Inbound Event Payload</h4>
              <JsonViewer data={selectedWebhook.payload} title="JSON Payload Ingestion" maxHeight="max-h-80" />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
