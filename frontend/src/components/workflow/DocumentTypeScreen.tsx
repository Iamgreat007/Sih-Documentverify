"use client";
import React, { useState } from 'react';
import { DocumentType } from '@/types';
import {
  ArrowLeft,
  ArrowRight,
  CreditCard,
  BookOpen,
  Car,
  FileText,
  XCircle,
  AlertTriangle,
  CheckCircle2,
  MinusCircle,
} from 'lucide-react';

// ── Public types ────────────────────────────────────────────────────
export type DocStatus = 'scanned' | 'na' | 'unchecked';

export interface DocChecklistEntry {
  docType: DocumentType;
  status: DocStatus;
  fileName: string;
}

export interface UnavailableDocFlags {
  aadhaar: boolean;
  driving_license: boolean;
  passport: boolean;
  visa: boolean;
}

interface DocumentTypeScreenProps {
  initialType: DocumentType;
  initialConfidence?: number;
  initialFileName?: string;
  onBack: () => void;
  /** primaryDoc = first "scanned" entry; checklist = full state; unavailable = N/A map */
  onContinue: (
    primaryDoc: DocumentType,
    fileName: string,
    unavailableDocs: UnavailableDocFlags,
    checklist: DocChecklistEntry[]
  ) => void;
}

// ── Static metadata ─────────────────────────────────────────────────
const DOC_OPTIONS: {
  type: DocumentType;
  label: string;
  desc: string;
  icon: React.ReactNode;
  accent: string;       // tw color name
}[] = [
  {
    type: 'aadhaar',
    label: 'Aadhaar Card',
    desc: 'UIDAI 12-digit national identity (Front/Back)',
    icon: <CreditCard className="w-5 h-5" />,
    accent: 'emerald',
  },
  {
    type: 'driving_license',
    label: 'Driving Licence',
    desc: 'Parivahan smart card licence (Front/Back)',
    icon: <Car className="w-5 h-5" />,
    accent: 'amber',
  },
  {
    type: 'passport',
    label: 'Passport',
    desc: 'ICAO 9303 biometric passport',
    icon: <BookOpen className="w-5 h-5" />,
    accent: 'blue',
  },
  {
    type: 'visa',
    label: 'Visa',
    desc: 'International travel entry permit / sticker',
    icon: <FileText className="w-5 h-5" />,
    accent: 'teal',
  },
];

const ACCENT_CLASSES: Record<string, { bg: string; text: string; border: string; light: string }> = {
  emerald: { bg: 'bg-emerald-600', text: 'text-emerald-700', border: 'border-emerald-500', light: 'bg-emerald-50' },
  amber:   { bg: 'bg-amber-500',   text: 'text-amber-700',   border: 'border-amber-500',   light: 'bg-amber-50'   },
  blue:    { bg: 'bg-blue-600',    text: 'text-blue-700',    border: 'border-blue-500',    light: 'bg-blue-50'    },
  teal:    { bg: 'bg-teal-600',    text: 'text-teal-700',    border: 'border-teal-500',    light: 'bg-teal-50'    },
};

// ── Component ────────────────────────────────────────────────────────
export default function DocumentTypeScreen({
  initialType,
  initialConfidence = 98,
  initialFileName,
  onBack,
  onContinue,
}: DocumentTypeScreenProps) {

  // Per-doc state: status + editable filename
  const [entries, setEntries] = useState<DocChecklistEntry[]>(
    DOC_OPTIONS.map((opt) => ({
      docType: opt.type,
      status: opt.type === initialType ? 'scanned' : 'unchecked',
      fileName: opt.type === initialType
        ? (initialFileName || `${opt.type}_001`)
        : `${opt.type}_001`,
    }))
  );

  // Which filename is being edited
  const [editingType, setEditingType] = useState<DocumentType | null>(null);

  // Derived helpers
  const scannedCount  = entries.filter(e => e.status === 'scanned').length;
  const naCount       = entries.filter(e => e.status === 'na').length;
  const allScanned    = entries.every(e => e.status === 'scanned');
  const noneScanned   = entries.every(e => e.status !== 'scanned');

  const setStatus = (type: DocumentType, status: DocStatus) => {
    setEntries(prev => prev.map(e => e.docType === type ? { ...e, status } : e));
  };

  const toggleStatus = (type: DocumentType) => {
    const cur = entries.find(e => e.docType === type)!;
    if (cur.status === 'unchecked') setStatus(type, 'scanned');
    else if (cur.status === 'scanned') setStatus(type, 'unchecked');
    // 'na' cannot be toggled via checkbox — use the N/A button
  };

  const toggleNA = (type: DocumentType) => {
    const cur = entries.find(e => e.docType === type)!;
    setStatus(type, cur.status === 'na' ? 'unchecked' : 'na');
  };

  const selectAll = () =>
    setEntries(prev => prev.map(e => ({ ...e, status: 'scanned' })));

  const clearAll = () =>
    setEntries(prev => prev.map(e => ({ ...e, status: 'unchecked' })));

  const updateFileName = (type: DocumentType, name: string) => {
    setEntries(prev => prev.map(e => e.docType === type ? { ...e, fileName: name } : e));
  };

  const handleContinue = () => {
    const primary = entries.find(e => e.status === 'scanned');
    if (!primary) return;
    const unavailable: UnavailableDocFlags = {
      aadhaar:         entries.find(e => e.docType === 'aadhaar')?.status === 'na',
      driving_license: entries.find(e => e.docType === 'driving_license')?.status === 'na',
      passport:        entries.find(e => e.docType === 'passport')?.status === 'na',
      visa:            entries.find(e => e.docType === 'visa')?.status === 'na',
    };
    onContinue(primary.docType, primary.fileName, unavailable, entries);
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 select-none">

      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-slate-200 flex-shrink-0">
        <button type="button" onClick={onBack}
          className="p-1 -ml-1 text-slate-600 hover:text-slate-900 flex items-center gap-1 text-xs font-semibold">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="text-center">
          <h2 className="text-sm font-bold text-slate-900">Document Checklist</h2>
          <p className="text-[10px] text-slate-500">Select all docs produced by applicant</p>
        </div>
        <div className="w-10" />
      </div>

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* N/A notice */}
        {naCount > 0 && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-2xl px-3.5 py-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <p className="text-[11px] font-semibold text-amber-800 leading-snug">
              {naCount} document{naCount > 1 ? 's' : ''} marked <strong>N/A</strong> — recorded in audit log.
            </p>
          </div>
        )}

        {/* Checklist rows */}
        <div className="space-y-2">
          {DOC_OPTIONS.map((opt) => {
            const entry  = entries.find(e => e.docType === opt.type)!;
            const ac     = ACCENT_CLASSES[opt.accent];
            const isScanned   = entry.status === 'scanned';
            const isNA        = entry.status === 'na';
            const isUnchecked = entry.status === 'unchecked';
            const isEditing   = editingType === opt.type;

            return (
              <div key={opt.type}
                className={`rounded-2xl border overflow-hidden transition-all ${
                  isNA
                    ? 'bg-slate-100/80 border-slate-300 opacity-75'
                    : isScanned
                    ? `bg-white ${ac.border} border-2 shadow-sm`
                    : 'bg-white border-slate-200'
                }`}>

                {/* Main row */}
                <div className="flex items-center p-3 gap-2">

                  {/* Checkbox */}
                  <button type="button"
                    disabled={isNA}
                    onClick={() => toggleStatus(opt.type)}
                    className="flex-shrink-0 p-0.5">
                    {isScanned ? (
                      <CheckCircle2 className={`w-5 h-5 ${ac.text}`} />
                    ) : isNA ? (
                      <MinusCircle className="w-5 h-5 text-slate-400" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-slate-300 bg-white" />
                    )}
                  </button>

                  {/* Icon */}
                  <div className={`p-2 rounded-xl flex-shrink-0 ${isNA ? 'bg-slate-200 text-slate-400' : `${ac.light} ${ac.text}`}`}>
                    {opt.icon}
                  </div>

                  {/* Label */}
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-bold truncate ${isNA ? 'text-slate-400 line-through' : 'text-slate-900'}`}>
                      {opt.label}
                    </p>
                    <p className="text-[10px] text-slate-500 truncate">{opt.desc}</p>
                  </div>

                  {/* N/A toggle */}
                  <button type="button"
                    onClick={() => toggleNA(opt.type)}
                    title={isNA ? 'Mark available' : 'Mark as not available'}
                    className={`flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-bold border flex-shrink-0 transition ${
                      isNA
                        ? 'bg-rose-100 border-rose-300 text-rose-700 hover:bg-rose-200'
                        : 'bg-slate-100 border-slate-300 text-slate-500 hover:bg-rose-50 hover:border-rose-300 hover:text-rose-600'
                    }`}>
                    <XCircle className="w-3 h-3" />
                    {isNA ? 'N/A' : 'N/A?'}
                  </button>
                </div>

                {/* N/A reason chip */}
                {isNA && (
                  <div className="px-3 pb-2.5 -mt-1">
                    <div className="bg-rose-50 border border-rose-200 rounded-xl px-3 py-1.5 flex items-center gap-2">
                      <XCircle className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />
                      <span className="text-[11px] font-semibold text-rose-700">
                        Not produced — logged as N/A in audit
                      </span>
                    </div>
                  </div>
                )}

                {/* Filename row (only when scanned) */}
                {isScanned && (
                  <div className={`px-3 pb-3 -mt-1 border-t ${ac.border} border-opacity-30 pt-2`}>
                    <p className="text-[9px] font-extrabold text-slate-400 uppercase tracking-wider mb-1">
                      📁 File name
                    </p>
                    {isEditing ? (
                      <input
                        autoFocus
                        type="text"
                        value={entry.fileName}
                        onChange={(e) => updateFileName(opt.type, e.target.value)}
                        onBlur={() => setEditingType(null)}
                        onKeyDown={(e) => { if (e.key === 'Enter') setEditingType(null); }}
                        className={`w-full px-2.5 py-1.5 rounded-xl border text-[11px] font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-offset-0 ${ac.border} focus:ring-${opt.accent}-400`}
                        placeholder={`${opt.type}_001`}
                      />
                    ) : (
                      <button type="button"
                        onClick={() => setEditingType(opt.type)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-xl border ${ac.border} border-opacity-40 ${ac.light} flex items-center justify-between group transition hover:border-opacity-100`}>
                        <span className={`text-[11px] font-mono font-semibold ${ac.text}`}>
                          {entry.fileName || `${opt.type}_001`}
                        </span>
                        <svg className="w-3 h-3 text-slate-400 group-hover:text-slate-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828A2 2 0 0110 16.414V18h1.586a2 2 0 001.414-.586l7-7a2 2 0 000-2.828l-1.172-1.172a2 2 0 00-2.828 0L9 13z" />
                        </svg>
                      </button>
                    )}
                    <p className="text-[9px] text-slate-400 mt-1 font-mono">Saved in: <span className="text-emerald-700">./image/</span></p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Bottom CTA ── */}
      <div className="flex-shrink-0 p-4 bg-white border-t border-slate-200">
        {scannedCount === 0 ? (
          <div className="text-center py-2 text-xs text-slate-500 font-medium">
            ✓ Check at least one document to continue
          </div>
        ) : (
          <button type="button" onClick={handleContinue}
            className="w-full py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 active:scale-98">
            <span>
              Continue with {scannedCount} doc{scannedCount !== 1 ? 's' : ''}
              {naCount > 0 ? ` · ${naCount} N/A` : ''}
            </span>
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
