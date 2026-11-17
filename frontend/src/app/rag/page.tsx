'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  User as UserIcon,
  Send,
  FileText,
  Sparkles,
  Shield,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RefreshCw
} from 'lucide-react';
import { api } from '@/lib/api';
import { SourceReference } from '@/types';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
  evidence_found?: boolean;
  timestamp: string;
}

const SAMPLE_QUESTIONS = [
  'What is the first-line therapy for Stage 1 hypertension?',
  'What LOINC code represents the blood pressure panel?',
  'What is MediSync AI\'s policy on modifying clinical records?',
  'Which calcium channel blockers are recommended for blood pressure?'
];

export default function RAGAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-init',
      sender: 'assistant',
      content: (
        'Hello! I am **MediSync AI Clinical Assistant**. I can answer inquiries grounded strictly in our ' +
        'indexed clinical knowledge base (Cardiovascular Guidelines, HL7 FHIR Specifications, Hospital SOPs). ' +
        'Every answer includes verified chunk citations with similarity relevance.'
      ),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!queryText) setInput('');
    setLoading(true);

    try {
      const res = await api.rag.queryAssistant(textToSend);
      const assistantMsg: Message = {
        id: `msg-res-${Date.now()}`,
        sender: 'assistant',
        content: res.answer,
        sources: res.sources,
        evidence_found: res.evidence_found,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <span>MediSync AI Clinical Assistant</span>
              <span className="px-1.5 py-0.5 rounded bg-teal-100 text-teal-800 text-[10px] font-extrabold uppercase">
                Grounded RAG
              </span>
            </h2>
            <p className="text-[11px] text-slate-500">
              pgvector 384-d semantic search • Zero hallucination fallback active
            </p>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2">
          <span className="text-xs text-slate-500 flex items-center gap-1 bg-white px-2.5 py-1 rounded-full border border-slate-200">
            <Shield className="w-3.5 h-3.5 text-teal-600" />
            <span>Document ACL Enforced</span>
          </span>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-3xl ${msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          >
            <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
              msg.sender === 'user'
                ? 'bg-slate-900 text-white'
                : 'bg-teal-600 text-white shadow-sm'
            }`}>
              {msg.sender === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            <div className="space-y-2 max-w-[85%]">
              <div className={`p-4 rounded-2xl text-xs leading-relaxed shadow-sm ${
                msg.sender === 'user'
                  ? 'bg-slate-900 text-white rounded-tr-none'
                  : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-none'
              }`}>
                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>
                <div className={`mt-2 text-[10px] ${msg.sender === 'user' ? 'text-slate-400' : 'text-slate-400'}`}>
                  {msg.timestamp}
                </div>
              </div>

              {/* Citations Accordion */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="p-3 bg-teal-50/60 rounded-xl border border-teal-200/60 text-xs space-y-2">
                  <button
                    onClick={() => toggleSources(msg.id)}
                    className="w-full flex items-center justify-between text-teal-900 font-bold text-[11px]"
                  >
                    <span className="flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-teal-700" />
                      <span>{msg.sources.length} Verified Evidence Sources</span>
                    </span>
                    {expandedSources[msg.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {expandedSources[msg.id] && (
                    <div className="space-y-2 pt-2 border-t border-teal-200/40">
                      {msg.sources.map((src, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-white border border-teal-100 text-[11px] space-y-1">
                          <div className="flex items-center justify-between font-semibold text-slate-800">
                            <span className="truncate max-w-[200px]">{src.document_title}</span>
                            <span className="text-[10px] bg-teal-100 text-teal-800 px-1.5 py-0.2 rounded font-mono">
                              Relevance: {(src.similarity_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-slate-600 italic text-[11px]">"{src.snippet}"</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <div className="w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-teal-600" />
              <span>Retrieving pgvector chunks and synthesizing grounded answer...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions Chips */}
      <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/50 flex gap-2 overflow-x-auto text-[11px]">
        {SAMPLE_QUESTIONS.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            className="px-2.5 py-1 rounded-full bg-white border border-slate-200 hover:border-teal-500 hover:text-teal-700 text-slate-600 transition-colors whitespace-nowrap shadow-2xs"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="p-3 border-t border-slate-200 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask medical or integration questions (e.g. 'What is the dosage for Lisinopril?')..."
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-teal-500 shadow-2xs"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2.5 rounded-xl bg-teal-600 text-white hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
