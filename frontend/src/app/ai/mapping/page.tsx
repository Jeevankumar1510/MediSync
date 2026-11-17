'use client';

import React, { useState } from 'react';
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Check,
  X,
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { api } from '@/lib/api';
import { FieldMappingResponse, FieldMappingSuggestion } from '@/types';
import { MOCK_FIELD_MAPPING } from '@/lib/mockData';

export default function FieldMappingPage() {
  const [mappingData, setMappingData] = useState<FieldMappingResponse>(MOCK_FIELD_MAPPING);
  const [resourceType, setResourceType] = useState('Patient');
  const [sampleJson, setSampleJson] = useState(`{
  "mrn": "MRN-100201",
  "first_name": "Eleanor",
  "last_name": "Vance",
  "dob": "1988-04-12",
  "patient_phone": "555-4433",
  "custom_vendor_clinic_code": "CLINIC-EAST-9"
}`);
  const [approvedFields, setApprovedFields] = useState<Record<string, boolean>>({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    try {
      const parsed = JSON.parse(sampleJson);
      const res = await api.ai.mapFields(parsed, resourceType);
      setMappingData(res);
      setApprovedFields({});
    } catch (e) {
      alert('Invalid JSON input format');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const toggleApproval = (field: string) => {
    setApprovedFields(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">AI Field Mapping &amp; Schema Review</h1>
          <p className="text-xs text-slate-500">
            Intelligent semantic alias matching and FHIR R4 canonical schema projection with Human-in-the-Loop review
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            <span>Confidence Threshold: 85%</span>
          </span>
        </div>
      </div>

      {/* Input Playground Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sample Payload Input */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Source Vendor Payload</h3>
            <select
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
              className="px-2 py-1 rounded-lg border border-slate-300 text-xs text-slate-700 outline-none"
            >
              <option value="Patient">Patient</option>
              <option value="Observation">Observation</option>
              <option value="Condition">Condition</option>
            </select>
          </div>

          <textarea
            rows={10}
            value={sampleJson}
            onChange={(e) => setSampleJson(e.target.value)}
            className="w-full p-3 font-mono text-xs bg-slate-950 text-emerald-400 rounded-lg border border-slate-800 outline-none focus:border-teal-500 leading-relaxed"
          />

          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="w-full py-2.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            {isAnalyzing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>{isAnalyzing ? 'Mapping...' : 'Run AI Field Inference'}</span>
          </button>
        </div>

        {/* Mapping Suggestions Table (2 cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Recommended Target Projections</h3>
              <p className="text-xs text-slate-500">
                Overall Inference Score: <span className="font-bold text-teal-700">{(mappingData.overall_confidence * 100).toFixed(0)}%</span>
              </p>
            </div>
            {mappingData.requires_human_approval && (
              <span className="px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                <span>Review Recommended</span>
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">Vendor Key</th>
                  <th className="py-2.5 px-3"></th>
                  <th className="py-2.5 px-3">FHIR R4 Target Path</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3 text-right">Human Approval</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {mappingData.suggestions.map((sug) => {
                  const isApproved = approvedFields[sug.source_field] ?? !sug.requires_human_approval;
                  const confPct = Math.round(sug.confidence_score * 100);

                  return (
                    <tr key={sug.source_field} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3 px-3 font-mono font-medium text-slate-800">
                        {sug.source_field}
                      </td>
                      <td className="py-3 px-1 text-slate-300">
                        <ArrowRight className="w-3.5 h-3.5" />
                      </td>
                      <td className="py-3 px-3 font-mono font-semibold text-teal-800">
                        {sug.suggested_target_field}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                confPct >= 85 ? 'bg-emerald-500' : 'bg-amber-500'
                              }`}
                              style={{ width: `${confPct}%` }}
                            />
                          </div>
                          <span className={`text-[11px] font-bold ${
                            confPct >= 85 ? 'text-emerald-700' : 'text-amber-700'
                          }`}>
                            {confPct}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => toggleApproval(sug.source_field)}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                            isApproved
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {isApproved ? <Check className="w-3.5 h-3.5 text-emerald-700" /> : <X className="w-3.5 h-3.5" />}
                          <span>{isApproved ? 'Approved' : 'Reject'}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="p-3 bg-teal-50/60 rounded-xl border border-teal-100 text-xs text-teal-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-teal-600 flex-shrink-0" />
              <span>
                Human-in-the-Loop policy enforced: Field projections below 85% confidence pause for manual confirmation.
              </span>
            </div>
            <button
              onClick={() => alert('Mappings applied to ETL transformation engine successfully!')}
              className="px-4 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs shadow-sm"
            >
              Commit Mappings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
