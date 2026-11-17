'use client';

import React, { useState, useEffect } from 'react';
import {
  FileText,
  Upload,
  Trash2,
  Lock,
  Globe,
  CheckCircle2,
  Clock,
  Sparkles,
  Layers,
  FileCheck
} from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { api } from '@/lib/api';
import { Document } from '@/types';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [title, setTitle] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    const res = await api.rag.listDocuments();
    setDocuments(res.items);
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    try {
      const doc = await api.rag.uploadDocument(file, title || file.name, isPublic);
      setDocuments([doc, ...documents]);
      setFile(null);
      setTitle('');
      setUploadNotice(`Indexed '${doc.title}' into ${doc.chunk_count} pgvector chunks.`);
      setTimeout(() => setUploadNotice(null), 5000);
    } catch (e) {
      alert('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document and all its pgvector embeddings?')) return;
    await api.rag.deleteDocument(id);
    setDocuments(documents.filter(d => d.id !== id));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Clinical Knowledge Base &amp; Vector Index</h1>
          <p className="text-xs text-slate-500">
            Persistent document ingestion with semantic chunking, 384-d pgvector embeddings, and ACL controls
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            <span>PostgreSQL pgvector (384-d)</span>
          </span>
        </div>
      </div>

      {uploadNotice && (
        <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs flex items-center gap-2 font-medium">
          <CheckCircle2 className="w-4 h-4 text-teal-600 flex-shrink-0" />
          <span>{uploadNotice}</span>
        </div>
      )}

      {/* Upload Zone */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Ingest Clinical Protocol or Technical Guide
        </h3>

        <form onSubmit={handleUpload} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Document Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Clinical Practice Guidelines for Type 2 Diabetes"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 outline-none focus:border-teal-500 text-xs"
                />
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 font-medium">
                  <input
                    type="checkbox"
                    checked={isPublic}
                    onChange={(e) => setIsPublic(e.target.checked)}
                    className="rounded text-teal-600 focus:ring-teal-500"
                  />
                  <span className="flex items-center gap-1">
                    {isPublic ? <Globe className="w-3.5 h-3.5 text-teal-600" /> : <Lock className="w-3.5 h-3.5 text-slate-400" />}
                    <span>Public to all clinical roles (otherwise private to uploader &amp; admin)</span>
                  </span>
                </label>
              </div>
            </div>

            {/* File Drop Area */}
            <div className="border-2 border-dashed border-slate-200 hover:border-teal-400 rounded-xl p-4 flex flex-col items-center justify-center text-center transition-colors bg-slate-50/50">
              <Upload className="w-6 h-6 text-slate-400 mb-1" />
              <input
                type="file"
                id="doc-file"
                required
                accept=".txt,.md,.json,.docx,.csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
              />
              <label
                htmlFor="doc-file"
                className="cursor-pointer text-xs font-semibold text-teal-600 hover:text-teal-700 block truncate max-w-[200px]"
              >
                {file ? file.name : 'Choose .txt, .md, .docx, .json'}
              </label>
              <p className="text-[10px] text-slate-400 mt-1">Up to 25MB per document</p>
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={!file || isUploading}
              className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              <Upload className="w-4 h-4" />
              <span>{isUploading ? 'Chunking & Embedding...' : 'Upload & Index'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Indexed Documents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Document Title</th>
                <th className="py-3 px-4">Filename</th>
                <th className="py-3 px-4">Format</th>
                <th className="py-3 px-4">Chunks</th>
                <th className="py-3 px-4">Access Control</th>
                <th className="py-3 px-4">Indexing Status</th>
                <th className="py-3 px-4">Indexed Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="py-3.5 px-4 font-semibold text-slate-900 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-teal-600 flex-shrink-0" />
                    <span>{doc.title}</span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                    {doc.filename}
                  </td>
                  <td className="py-3.5 px-4 font-mono uppercase text-slate-600">
                    {doc.file_type}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 font-semibold font-mono text-[11px]">
                      {doc.chunk_count} chunks
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    {doc.is_public ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-teal-700">
                        <Globe className="w-3 h-3" />
                        <span>Public</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500">
                        <Lock className="w-3 h-3" />
                        <span>Private</span>
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={doc.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                      title="Delete document and vector chunks"
                    >
                      <Trash2 className="w-4 h-4" />
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
