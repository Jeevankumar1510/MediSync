'use client';

import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  Plus,
  FileText,
  Activity,
  Calendar,
  Phone,
  Mail,
  MapPin,
  CheckCircle2,
  ChevronRight,
  Eye
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Modal } from '@/components/ui/Modal';
import { JsonViewer } from '@/components/ui/JsonViewer';
import { api } from '@/lib/api';
import { Patient, PatientRecord } from '@/types';

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [records, setRecords] = useState<PatientRecord[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<PatientRecord | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isRecordModalOpen, setIsRecordModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // New Patient Form
  const [formData, setFormData] = useState({
    mrn: '',
    first_name: '',
    last_name: '',
    birth_date: '1988-05-20',
    gender: 'female',
    phone: '555-0155',
    email: 'new.patient@example.com',
    city: 'Boston',
    state: 'MA'
  });

  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients() {
    try {
      const data = await api.patients.list();
      setPatients(data.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const handleViewRecords = async (patient: Patient) => {
    setSelectedPatient(patient);
    const recs = await api.patients.getRecords(patient.id);
    setRecords(recs);
    setSelectedRecord(recs[0] || null);
    setIsRecordModalOpen(true);
  };

  const handleCreatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    const created = await api.patients.create({
      mrn: formData.mrn || `MRN-${Math.floor(100000 + Math.random() * 900000)}`,
      first_name: formData.first_name,
      last_name: formData.last_name,
      birth_date: formData.birth_date,
      gender: formData.gender,
      contact_info: { phone: formData.phone, email: formData.email },
      address: { city: formData.city, state: formData.state }
    });
    setPatients([created, ...patients]);
    setIsAddModalOpen(false);
  };

  const filteredPatients = patients.filter(p =>
    p.mrn.toLowerCase().includes(searchTerm.toLowerCase()) ||
    `${p.first_name} ${p.last_name}`.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Patient Clinical Records</h1>
          <p className="text-xs text-slate-500">
            Standardized FHIR R4 demographic registry with deterministic checksum deduplication
          </p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-teal-600 text-white text-xs font-semibold hover:bg-teal-700 transition-colors shadow-sm self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Register Patient</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-sm flex items-center gap-3">
        <Search className="w-4 h-4 text-slate-400 ml-1" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter by MRN (e.g. MRN-100201) or patient name..."
          className="flex-1 text-xs text-slate-800 placeholder-slate-400 bg-transparent outline-none"
        />
        {searchTerm && (
          <button
            onClick={() => setSearchTerm('')}
            className="text-xs text-slate-400 hover:text-slate-600 px-2"
          >
            Clear
          </button>
        )}
      </div>

      {/* Patient Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3.5 px-4">Medical Record #</th>
                <th className="py-3.5 px-4">Patient Name</th>
                <th className="py-3.5 px-4">Birth Date</th>
                <th className="py-3.5 px-4">Gender</th>
                <th className="py-3.5 px-4">Location</th>
                <th className="py-3.5 px-4">Clinical Records</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredPatients.map((patient) => (
                <tr key={patient.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-teal-700">
                    {patient.mrn}
                  </td>
                  <td className="py-3.5 px-4 font-medium text-slate-900">
                    {patient.first_name} {patient.last_name}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500">
                    {patient.birth_date}
                  </td>
                  <td className="py-3.5 px-4 capitalize text-slate-600">
                    {patient.gender}
                  </td>
                  <td className="py-3.5 px-4 text-slate-500">
                    {patient.address?.city || 'Boston'}, {patient.address?.state || 'MA'}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold text-[11px]">
                      {patient.record_count || 3} resources
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={patient.is_active ? 'ACTIVE' : 'INACTIVE'} size="sm" />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleViewRecords(patient)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-50 text-teal-700 text-xs font-semibold hover:bg-teal-100 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>FHIR Records</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Patient Clinical Records Modal */}
      <Modal
        isOpen={isRecordModalOpen}
        onClose={() => setIsRecordModalOpen(false)}
        title={`Clinical Records — ${selectedPatient?.first_name} ${selectedPatient?.last_name} (${selectedPatient?.mrn})`}
        maxWidth="max-w-4xl"
      >
        <div className="space-y-4">
          <div className="flex gap-2 border-b border-slate-200 pb-2 overflow-x-auto">
            {records.map((r, idx) => (
              <button
                key={r.id}
                onClick={() => setSelectedRecord(r)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  selectedRecord?.id === r.id
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <span>{r.resource_type} #{idx + 1}</span>
                <span className="text-[10px] opacity-75">({r.fhir_version})</span>
              </button>
            ))}
          </div>

          {selectedRecord && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Resource</span>
                  <span className="font-bold text-slate-800">{selectedRecord.resource_type}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">FHIR Version</span>
                  <span className="font-bold text-slate-800">{selectedRecord.fhir_version}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">SHA-256 Checksum</span>
                  <span className="font-mono text-slate-600 text-[10px] truncate block" title={selectedRecord.checksum}>
                    {selectedRecord.checksum?.slice(0, 16)}...
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Status</span>
                  <StatusBadge status={selectedRecord.status} size="sm" />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-xs font-bold text-slate-800 mb-1.5">Raw Source Ingestion</h4>
                  <JsonViewer data={selectedRecord.raw_payload} title="Vendor EHR Payload" maxHeight="max-h-72" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800 mb-1.5">Normalized HL7 FHIR R4</h4>
                  <JsonViewer data={selectedRecord.normalized_payload} title="FHIR R4 Schema Validated" maxHeight="max-h-72" />
                </div>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Add Patient Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Register New Clinical Patient"
      >
        <form onSubmit={handleCreatePatient} className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-600 font-semibold mb-1">First Name</label>
              <input
                type="text"
                required
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500"
                placeholder="Jane"
              />
            </div>
            <div>
              <label className="block text-slate-600 font-semibold mb-1">Last Name</label>
              <input
                type="text"
                required
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500"
                placeholder="Doe"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-600 font-semibold mb-1">Medical Record Number (MRN)</label>
              <input
                type="text"
                value={formData.mrn}
                onChange={(e) => setFormData({ ...formData, mrn: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500 font-mono"
                placeholder="MRN-100204 (Auto-generated if blank)"
              />
            </div>
            <div>
              <label className="block text-slate-600 font-semibold mb-1">Birth Date</label>
              <input
                type="date"
                required
                value={formData.birth_date}
                onChange={(e) => setFormData({ ...formData, birth_date: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-600 font-semibold mb-1">Gender</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-600 font-semibold mb-1">Telephone</label>
              <input
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(false)}
              className="px-4 py-2 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-teal-600 text-white font-semibold hover:bg-teal-700 transition-colors shadow-sm"
            >
              Register Patient
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
