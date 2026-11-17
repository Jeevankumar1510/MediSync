'use client';

import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  HeartPulse,
  Activity,
  FileQuestion,
  HelpCircle,
  Lightbulb,
  CheckCircle2,
  ShieldCheck
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MOCK_QUALITY_REPORT } from '@/lib/mockData';
import { DataQualityReport } from '@/types';

export default function DataQualityPage() {
  const [report, setReport] = useState<DataQualityReport>(MOCK_QUALITY_REPORT);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<{ impact: string; remediation: string } | null>({
    impact: 'Systolic measurement of 188 mmHg indicates severe Stage 3 hypertensive urgency. Immediate triage review required.',
    remediation: 'Confirm with secondary automated cuff or manual sphygmomanometer. Ensure LOINC 85354-9 vital panel is linked.'
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">AI Clinical Data Quality &amp; Anomaly Inspector</h1>
          <p className="text-xs text-slate-500">
            Unsupervised Scikit-learn IsolationForest anomaly detection on vital sign streams and missing field audits
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
            <span>1 Outlier Requiring Clinical Review</span>
          </span>
        </div>
      </div>

      {/* Strict Non-Mutation Safety Callout */}
      <div className="p-4 rounded-xl bg-slate-900 text-slate-200 text-xs flex items-start gap-3 border border-slate-800">
        <ShieldCheck className="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-white text-xs">Healthcare Data Integrity Policy</h4>
          <p className="text-slate-300 text-[11px] leading-relaxed">
            MediSync AI operates in strict read-only analytical mode. Outlier flags and quality scores are recorded for
            clinical alerting and data pipeline monitoring only. The system strictly never alters, mutates, or truncates primary EHR records.
          </p>
        </div>
      </div>

      {/* Quality Score Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Quality Score</span>
          <p className="mt-1 text-3xl font-bold text-teal-700">{(report.quality_score * 100).toFixed(0)}%</p>
          <p className="mt-1 text-xs text-slate-500">Calculated across 8 FHIR Observation elements</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Anomalies Detected</span>
          <p className="mt-1 text-3xl font-bold text-rose-600">{report.anomalies_detected.length}</p>
          <p className="mt-1 text-xs text-slate-500">IsolationForest multi-variate vitals outlier</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Missing FHIR Elements</span>
          <p className="mt-1 text-3xl font-bold text-amber-600">{report.missing_fields.length}</p>
          <p className="mt-1 text-xs text-slate-500">Non-critical schema attributes</p>
        </div>
      </div>

      {/* Anomalies Detailed Table */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Statistical Clinical Outlier Stream</h3>
            <p className="text-xs text-slate-500">Flagged records exceeding standard physiological standard deviations</p>
          </div>
          <StatusBadge status="ACTIVE AUDIT" size="sm" />
        </div>

        <div className="space-y-3">
          {report.anomalies_detected.map((anomaly, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-rose-200 bg-rose-50/40 text-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-rose-100 text-rose-700">
                    <HeartPulse className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="font-bold text-rose-900 uppercase tracking-wide text-xs">
                      {anomaly.field} Measurement Outlier
                    </span>
                    <span className="ml-2 font-mono text-[11px] bg-rose-200/60 text-rose-800 px-2 py-0.5 rounded">
                      Observed: {anomaly.observed_value} mmHg
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 text-[11px]">Normal: {anomaly.expected_range}</span>
                  <StatusBadge status={anomaly.clinical_risk} size="sm" />
                </div>
              </div>

              <p className="text-slate-700 leading-relaxed text-[11px]">
                {anomaly.description}
              </p>

              {explanation && (
                <div className="pt-3 border-t border-rose-200/60 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-2.5 rounded-lg bg-white/80 border border-rose-200/40">
                    <span className="font-bold text-rose-950 flex items-center gap-1.5 text-[11px] mb-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                      <span>Clinical Impact</span>
                    </span>
                    <p className="text-slate-600 text-[11px]">{explanation.impact}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white/80 border border-teal-200/40">
                    <span className="font-bold text-teal-950 flex items-center gap-1.5 text-[11px] mb-1">
                      <Lightbulb className="w-3.5 h-3.5 text-teal-600" />
                      <span>Remediation Advice</span>
                    </span>
                    <p className="text-slate-600 text-[11px]">{explanation.remediation}</p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Missing Schema Attributes Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900">Missing Mandatory &amp; Advisory FHIR Elements</h3>
        <p className="text-xs text-slate-500">Non-blocking attributes flagged for vendor integration enrichment</p>

        <div className="flex flex-wrap gap-2 pt-1">
          {report.missing_fields.map((field) => (
            <span
              key={field}
              className="px-3 py-1 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs font-mono font-medium flex items-center gap-1.5"
            >
              <FileQuestion className="w-3.5 h-3.5 text-amber-600" />
              <span>{field}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
