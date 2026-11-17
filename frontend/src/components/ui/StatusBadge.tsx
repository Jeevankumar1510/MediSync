import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const norm = (status || '').toUpperCase();

  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  let dot = 'bg-slate-400';

  if (['COMPLETED', 'INDEXED', 'ACTIVE', 'HEALTHY', 'FINAL', 'PROCESSED', 'CONNECTED'].includes(norm)) {
    bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    dot = 'bg-emerald-500';
  } else if (['PENDING', 'PROCESSING', 'RETRYING', 'MEDIUM', 'OAUTH2'].includes(norm)) {
    bg = 'bg-amber-50 text-amber-700 border-amber-200';
    dot = 'bg-amber-500';
  } else if (['FAILED', 'HIGH', 'UNHEALTHY', 'ERROR', 'DISCONNECTED'].includes(norm)) {
    bg = 'bg-rose-50 text-rose-700 border-rose-200';
    dot = 'bg-rose-500';
  } else if (['FHIR_R4', 'VENDOR_REST', 'LOW', 'RECEIVED', 'BEARER_TOKEN'].includes(norm)) {
    bg = 'bg-sky-50 text-sky-700 border-sky-200';
    dot = 'bg-sky-500';
  }

  const px = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${bg} ${px}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status}
    </span>
  );
};
