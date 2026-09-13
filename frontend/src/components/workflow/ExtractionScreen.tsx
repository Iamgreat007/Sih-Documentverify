"use client";
import React, { useState } from 'react';
import { DocumentType, ExtractedField } from '@/types';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Edit2,
  Sparkles,
  AlertTriangle,
  CreditCard,
  BookOpen,
  Car,
  FileText,
  XCircle,
} from 'lucide-react';
import { DocChecklistEntry } from '@/components/workflow/DocumentTypeScreen';
import { CapturedDoc } from '@/components/scanner/WebCamScanner';

// ── Doc metadata ─────────────────────────────────────────────────────
const DOC_META: Record<string, {
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  accent: { tab: string; ring: string; badge: string; img: string };
}> = {
  aadhaar: {
    label: 'Aadhaar Card',
    shortLabel: 'Aadhaar',
    icon: <CreditCard className="w-3.5 h-3.5" />,
    accent: {
      tab:   'bg-emerald-600 text-white',
      ring:  'border-emerald-500 ring-emerald-500/20',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      img:   'border-emerald-200',
    },
  },
  driving_license: {
    label: 'Driving Licence',
    shortLabel: 'DL',
    icon: <Car className="w-3.5 h-3.5" />,
    accent: {
      tab:   'bg-amber-500 text-white',
      ring:  'border-amber-400 ring-amber-400/20',
      badge: 'bg-amber-50 text-amber-700 border-amber-200',
      img:   'border-amber-200',
    },
  },
  passport: {
    label: 'Passport',
    shortLabel: 'Passport',
    icon: <BookOpen className="w-3.5 h-3.5" />,
    accent: {
      tab:   'bg-blue-600 text-white',
      ring:  'border-blue-500 ring-blue-500/20',
      badge: 'bg-blue-50 text-blue-700 border-blue-200',
      img:   'border-blue-200',
    },
  },
  visa: {
    label: 'Visa',
    shortLabel: 'Visa',
    icon: <FileText className="w-3.5 h-3.5" />,
    accent: {
      tab:   'bg-teal-600 text-white',
      ring:  'border-teal-500 ring-teal-500/20',
      badge: 'bg-teal-50 text-teal-700 border-teal-200',
      img:   'border-teal-200',
    },
  },
};

// ── Props ─────────────────────────────────────────────────────────────
interface ExtractionScreenProps {
  documentType: DocumentType;
  fileName: string;
  documentImage: string;
  backImage?: string;
  initialFields: Record<string, ExtractedField>;
  // Multi-doc session
  sessionChecklist?: DocChecklistEntry[];
  allDocFields?: Record<string, Record<string, ExtractedField>>;
  sessionDocs?: CapturedDoc[];
  onBack: () => void;
  onProceedToVerification: (updatedFields: Record<string, ExtractedField>) => void;
}

// ── Editable fields panel ─────────────────────────────────────────────
function FieldsPanel({
  fields,
  onUpdate,
  accent,
}: {
  fields: Record<string, ExtractedField>;
  onUpdate: (updated: Record<string, ExtractedField>) => void;
  accent: typeof DOC_META.aadhaar.accent;
}) {
  const [localFields, setLocalFields] = useState(fields);
  const [editingKey, setEditingKey] = useState<string | null>(null);

  const handleChange = (key: string, value: string) => {
    const updated = { ...localFields, [key]: { ...localFields[key], value } };
    setLocalFields(updated);
    onUpdate(updated);
  };

  const fieldKeys = Object.keys(localFields);

  return (
    <div className="space-y-2">
      {fieldKeys.map((key) => {
        const field = localFields[key];
        if (!field) return null;
        const isEditing = editingKey === key;
        const highConf = field.confidence >= 90;

        return (
          <div
            key={key}
            className={`bg-white rounded-2xl p-3 border transition-all ${
              isEditing
                ? `${accent.ring} border-2 ring-2 shadow-sm`
                : 'border-slate-200/90 shadow-xs'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-slate-500">{field.label}</span>
              <div className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                highConf ? accent.badge : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                {highConf
                  ? <CheckCircle2 className="w-3 h-3" />
                  : <AlertTriangle className="w-3 h-3 text-amber-600" />}
                {field.confidence}%
              </div>
            </div>

            {isEditing ? (
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="text"
                  value={field.value}
                  autoFocus
                  onChange={(e) => handleChange(key, e.target.value)}
                  onBlur={() => setEditingKey(null)}
                  onKeyDown={(e) => { if (e.key === 'Enter') setEditingKey(null); }}
                  className="flex-1 px-2.5 py-1 rounded-lg border border-emerald-500 font-semibold text-xs text-slate-900 focus:outline-none"
                />
                <button type="button" onClick={() => setEditingKey(null)}
                  className="text-xs font-bold text-emerald-600 px-2 py-1 hover:bg-emerald-50 rounded">
                  Done
                </button>
              </div>
            ) : (
              <div onClick={() => setEditingKey(key)}
                className="flex items-center justify-between cursor-pointer group py-0.5">
                <span className="text-xs font-bold text-slate-900 leading-snug">{field.value}</span>
                <Edit2 className="w-3.5 h-3.5 text-slate-400 opacity-60 group-hover:opacity-100 group-hover:text-emerald-600 transition ml-2 flex-shrink-0" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────
export default function ExtractionScreen({
  documentType,
  fileName,
  documentImage,
  backImage,
  initialFields,
  sessionChecklist = [],
  allDocFields = {},
  sessionDocs = [],
  onBack,
  onProceedToVerification,
}: ExtractionScreenProps) {

  // Build the tab list from checklist (only scanned docs)
  const scannedEntries = sessionChecklist.filter(e => e.status === 'scanned');
  const naEntries      = sessionChecklist.filter(e => e.status === 'na');

  // If no checklist provided, fall back to single-doc mode
  const tabDocs = scannedEntries.length > 0
    ? scannedEntries
    : [{ docType: documentType, status: 'scanned' as const, fileName }];

  // Active tab
  const [activeDocType, setActiveDocType] = useState<DocumentType>(
    tabDocs[0]?.docType || documentType
  );

  // Per-doc field overrides (user edits)
  const [fieldOverrides, setFieldOverrides] = useState<Record<string, Record<string, ExtractedField>>>({});

  // Merged fields for active tab
  const getFields = (dt: DocumentType): Record<string, ExtractedField> => {
    const base = allDocFields[dt] || (dt === documentType ? initialFields : {});
    return { ...(base || {}), ...(fieldOverrides[dt] || {}) };
  };

  const handleUpdate = (dt: DocumentType, updated: Record<string, ExtractedField>) => {
    setFieldOverrides(prev => ({ ...prev, [dt]: updated }));
  };

  const handleProceed = () => {
    const primaryFields = getFields(documentType);
    onProceedToVerification(primaryFields);
  };

  const activeMeta    = DOC_META[activeDocType] ?? DOC_META.passport;
  const activeEntry   = tabDocs.find(e => e.docType === activeDocType);
  const activeFields  = getFields(activeDocType);
  const fieldCount    = Object.keys(activeFields).length;

  // Find scan images for active doc
  const frontDoc = sessionDocs.find(d => d.docType === activeDocType && (d.side === 'front' || d.side === 'single'));
  const backDoc  = sessionDocs.find(d => d.docType === activeDocType && d.side === 'back');
  const frontImg = frontDoc?.processedImage || frontDoc?.rawImage || documentImage;
  const backImg  = backDoc?.processedImage  || backDoc?.rawImage  || (activeDocType === documentType ? backImage : undefined);

  const [activeSide, setActiveSide] = useState<'front' | 'back'>('front');

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 select-none">

      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-slate-200 flex-shrink-0">
        <button type="button" onClick={onBack}
          className="p-1 -ml-1 text-slate-600 hover:text-slate-900 flex items-center gap-1 text-xs font-semibold">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="text-center">
          <h2 className="text-sm font-bold text-slate-900">Extracted Information</h2>
          <p className="text-[10px] text-slate-500">
            {tabDocs.length} doc{tabDocs.length !== 1 ? 's' : ''} scanned
            {naEntries.length > 0 ? ` · ${naEntries.length} N/A` : ''}
          </p>
        </div>
        <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200 max-w-[80px] truncate">
          {activeEntry?.fileName || fileName}
        </span>
      </div>

      {/* ── Doc Tabs ── */}
      {tabDocs.length > 1 && (
        <div className="flex-shrink-0 px-3 py-2 bg-white border-b border-slate-100 flex gap-1.5 overflow-x-auto scrollbar-none">
          {tabDocs.map((entry) => {
            const m = DOC_META[entry.docType] ?? DOC_META.passport;
            const isActive = activeDocType === entry.docType;
            const fCount = Object.keys(getFields(entry.docType)).length;
            return (
              <button key={entry.docType} type="button"
                onClick={() => { setActiveDocType(entry.docType as DocumentType); setActiveSide('front'); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap flex-shrink-0 transition border ${
                  isActive
                    ? `${m.accent.tab} border-transparent shadow-sm`
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}>
                {m.icon}
                {m.shortLabel}
                <span className={`text-[9px] px-1 py-0.5 rounded-full font-black ${
                  isActive ? 'bg-white/30' : 'bg-slate-100 text-slate-500'
                }`}>
                  {fCount}
                </span>
              </button>
            );
          })}

          {/* N/A docs shown as muted pills */}
          {naEntries.map((entry) => {
            const m = DOC_META[entry.docType] ?? DOC_META.passport;
            return (
              <div key={entry.docType}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap flex-shrink-0 bg-slate-100 text-slate-400 border border-slate-200 opacity-60">
                <XCircle className="w-3 h-3 text-rose-400" />
                {m.shortLabel}
                <span className="text-[9px] text-rose-400 font-bold">N/A</span>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Document image preview */}
        <div className="w-full bg-white rounded-2xl p-2.5 border border-slate-200 shadow-xs">
          {backImg && (
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Preview Source</span>
              <div className="flex gap-1 bg-slate-100 p-0.5 rounded-lg text-[10px] font-bold">
                {(['front', 'back'] as const).map(s => (
                  <button key={s} type="button" onClick={() => setActiveSide(s)}
                    className={`px-2 py-0.5 rounded capitalize transition ${
                      activeSide === s ? 'bg-white text-slate-950 shadow-xs' : 'text-slate-500 hover:text-slate-900'
                    }`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className={`relative w-full rounded-xl overflow-hidden border ${activeMeta.accent.img}`}>
            <img
              src={activeSide === 'back' && backImg ? backImg : frontImg}
              alt="Document source"
              className="w-full h-32 object-contain"
            />
            <div className="absolute top-2 left-2 bg-slate-950/70 text-white text-[9px] font-medium px-2 py-0.5 rounded flex items-center gap-1">
              <Sparkles className="w-2.5 h-2.5 text-emerald-400" />
              OCR Frame — {activeMeta.shortLabel} {activeSide.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Fields header */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-extrabold text-slate-500 uppercase tracking-wider">
            AI Extracted Fields
          </span>
          <div className="flex items-center gap-1.5">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${activeMeta.accent.badge}`}>
              {fieldCount} fields
            </span>
            <span className="text-[10px] text-slate-400">Tap to edit</span>
          </div>
        </div>

        {/* No fields fallback */}
        {fieldCount === 0 ? (
          <div className="bg-white rounded-2xl p-6 border border-slate-200 text-center text-slate-400">
            <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-300" />
            <p className="text-xs font-semibold">No fields extracted yet</p>
          </div>
        ) : (
          <FieldsPanel
            key={activeDocType}
            fields={activeFields}
            onUpdate={(updated) => handleUpdate(activeDocType as DocumentType, updated)}
            accent={activeMeta.accent}
          />
        )}
      </div>

      {/* ── Bottom CTA ── */}
      <div className="flex-shrink-0 p-4 bg-white border-t border-slate-200">
        <button type="button" onClick={handleProceed}
          className="w-full py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 active:scale-98">
          <span>Proceed to Verification</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
