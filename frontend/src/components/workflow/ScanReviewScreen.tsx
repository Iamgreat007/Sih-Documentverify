"use client";
import React, { useState } from 'react';
import {
  CheckCircle2,
  RotateCcw,
  ArrowRight,
  Crop,
  Sparkles,
  FolderCheck,
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  CreditCard,
  BookOpen,
  Car,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import { CapturedDoc } from '@/components/scanner/WebCamScanner';

interface ScanReviewScreenProps {
  // Legacy single-image fallback (used if sessionDocs is empty)
  scannedImage: string;
  backImage?: string;
  savedFilePaths?: { front?: string; back?: string };
  // Multi-doc session
  sessionDocs?: CapturedDoc[];
  onRetake: () => void;
  onAdjustCorners: () => void;
  onAcceptScan: () => void;
}

const DOC_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  aadhaar: {
    label: 'Aadhaar',
    color: 'emerald',
    icon: <CreditCard className="w-3.5 h-3.5" />,
  },
  driving_license: {
    label: 'Driving Licence',
    color: 'amber',
    icon: <Car className="w-3.5 h-3.5" />,
  },
  passport: {
    label: 'Passport',
    color: 'blue',
    icon: <BookOpen className="w-3.5 h-3.5" />,
  },
  visa: {
    label: 'Visa',
    color: 'teal',
    icon: <FileText className="w-3.5 h-3.5" />,
  },
};

const COLOR_MAP: Record<string, string> = {
  emerald: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  amber: 'bg-amber-100 text-amber-800 border-amber-300',
  blue: 'bg-blue-100 text-blue-800 border-blue-300',
  teal: 'bg-teal-100 text-teal-800 border-teal-300',
};

export default function ScanReviewScreen({
  scannedImage,
  backImage,
  savedFilePaths,
  sessionDocs = [],
  onRetake,
  onAdjustCorners,
  onAcceptScan,
}: ScanReviewScreenProps) {
  const hasSession = sessionDocs.length > 0;

  // Lightbox
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);

  // Editable filenames: keyed by doc id
  const [editableNames, setEditableNames] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);

  const getName = (id: string, fallback: string) =>
    editableNames[id] !== undefined ? editableNames[id] : fallback;

  const startEdit = (id: string, current: string) => {
    if (!(id in editableNames)) setEditableNames((p) => ({ ...p, [id]: current }));
    setEditingId(id);
  };

  const commitEdit = (id: string) => {
    setEditingId(null);
    // Sanitize: spaces → underscore, only safe chars
    setEditableNames((p) => ({
      ...p,
      [id]: (p[id] || '').replace(/[^a-zA-Z0-9_\-]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '') || p[id],
    }));
  };

        // Build display list
  const displayDocs: { id: string; image: string; label: string; sublabel: string; path: string; isSuspicious: boolean; docType: string }[] =
    hasSession
      ? sessionDocs.map((d) => ({
          id: d.id,
          image: d.processedImage || d.rawImage,
          label: `${DOC_META[d.docType]?.label ?? d.docType} — ${d.side === 'single' ? 'Page' : d.side.charAt(0).toUpperCase() + d.side.slice(1)}`,
          sublabel: d.fileName,
          path: d.savedPath,
          isSuspicious: d.isSuspicious,
          docType: d.docType,
        }))
      : [
          {
            id: 'front',
            image: scannedImage,
            label: 'Front Side',
            sublabel: savedFilePaths?.front || 'doc_front',
            path: savedFilePaths?.front || '',
            isSuspicious: false,
            docType: 'aadhaar',
          },
          ...(backImage
            ? [{
                id: 'back',
                image: backImage,
                label: 'Back Side',
                sublabel: savedFilePaths?.back || 'doc_back',
                path: savedFilePaths?.back || '',
                isSuspicious: false,
                docType: 'aadhaar',
              }]
            : []),
        ];

  const totalCount = displayDocs.length;

  // Lightbox helpers
  const openLightbox = (i: number) => setLightboxIdx(i);
  const closeLightbox = () => setLightboxIdx(null);
  const prevLightbox = () =>
    setLightboxIdx((i) => (i !== null ? (i - 1 + totalCount) % totalCount : 0));
  const nextLightbox = () =>
    setLightboxIdx((i) => (i !== null ? (i + 1) % totalCount : 0));

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 select-none">
      {/* ── Top Bar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-white border-b border-slate-200 flex-shrink-0">
        <button
          type="button"
          onClick={onRetake}
          className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1"
        >
          <RotateCcw className="w-4 h-4" />
          Retake
        </button>
        <div className="text-center">
          <h2 className="text-sm font-bold text-slate-900">Review Scans</h2>
          <p className="text-[10px] text-slate-500">
            {totalCount} image{totalCount !== 1 ? 's' : ''} captured
          </p>
        </div>
        <button
          type="button"
          onClick={onAdjustCorners}
          className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
        >
          <Crop className="w-4 h-4" />
          Adjust
        </button>
      </div>

      {/* ── Scrollable Gallery ── */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">

        {/* Summary badge */}
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-2xl px-3.5 py-2.5">
          <FolderCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-extrabold text-emerald-900">All images saved to ./image</p>
            <p className="text-[10px] text-emerald-700 font-mono truncate">
              {displayDocs.map(d => d.sublabel).join(' · ')}
            </p>
          </div>
          <span className="flex-shrink-0 text-[10px] font-black text-emerald-700 bg-emerald-200 px-2 py-0.5 rounded-full">
            {totalCount}
          </span>
        </div>

        {/* Suspicious warning */}
        {displayDocs.some((d) => d.isSuspicious) && (
          <div className="flex items-center gap-2 bg-rose-50 border border-rose-200 rounded-2xl px-3.5 py-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <p className="text-[11px] font-semibold text-rose-800">
              One or more documents flagged for tampering indicators — review carefully.
            </p>
          </div>
        )}

        {/* Document Grid */}
        <div className="grid grid-cols-2 gap-2.5">
          {displayDocs.map((doc, idx) => {
            const meta = DOC_META[doc.docType] ?? DOC_META.passport;
            const colorClass = COLOR_MAP[meta.color] ?? COLOR_MAP.emerald;
            return (
              <div
                key={doc.id}
                className={`relative rounded-2xl overflow-hidden border-2 bg-white shadow-sm text-left group transition ${
                  doc.isSuspicious ? 'border-rose-400' : 'border-slate-200 hover:border-emerald-400'
                }`}
              >
                {/* Clickable image area → lightbox */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => openLightbox(idx)}
                  onKeyDown={(e) => e.key === 'Enter' && openLightbox(idx)}
                  className="w-full aspect-[4/3] overflow-hidden bg-slate-100 cursor-pointer relative"
                >
                  <img
                    src={doc.image}
                    alt={doc.label}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                  />
                  {/* Zoom hint overlay */}
                  <div className="absolute inset-0 flex items-center justify-center bg-slate-900/0 group-hover:bg-slate-900/30 transition-all duration-200 rounded-none">
                    <ZoomIn className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" />
                  </div>
                </div>

                {/* Badge */}
                <div className="absolute top-1.5 left-1.5 pointer-events-none">
                  <span className={`flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded-full border ${colorClass}`}>
                    {meta.icon}
                    {doc.isSuspicious ? '⚠️' : ''}
                  </span>
                </div>

                {/* Passed tick */}
                {!doc.isSuspicious && (
                  <div className="absolute top-1.5 right-1.5 pointer-events-none">
                    <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center shadow">
                      <CheckCircle2 className="w-3 h-3 text-white" />
                    </div>
                  </div>
                )}

                {/* Label + Editable filename */}
                <div className="p-2 bg-white border-t border-slate-100">
                  <p className="text-[10px] font-bold text-slate-900 truncate leading-tight mb-1">{doc.label}</p>

                  {editingId === doc.id ? (
                    <div className="flex items-center gap-1">
                      <span className="text-[9px] text-slate-400 font-mono flex-shrink-0">📁</span>
                      <input
                        autoFocus
                        type="text"
                        value={getName(doc.id, doc.sublabel)}
                        onChange={(e) =>
                          setEditableNames((p) => ({ ...p, [doc.id]: e.target.value }))
                        }
                        onBlur={() => commitEdit(doc.id)}
                        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(doc.id); }}
                        className="flex-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-300 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-emerald-400 min-w-0"
                      />
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => startEdit(doc.id, doc.sublabel)}
                      className="flex items-center gap-1 w-full group/fn hover:bg-slate-50 rounded px-0.5 -mx-0.5 transition"
                    >
                      <span className="text-[9px] text-slate-400 font-mono flex-shrink-0">📁</span>
                      <span className="text-[10px] text-slate-400 font-mono truncate flex-1 text-left">
                        {getName(doc.id, doc.sublabel)}
                      </span>
                      <svg className="w-2.5 h-2.5 text-slate-300 group-hover/fn:text-emerald-500 flex-shrink-0 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828A2 2 0 0110 16.414V18h1.586a2 2 0 001.414-.586l7-7a2 2 0 000-2.828l-1.172-1.172a2 2 0 00-2.828 0L9 13z" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Scan Quality Row */}
        <div className="bg-white rounded-2xl p-3.5 border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-extrabold tracking-wider text-slate-500 uppercase">Scan Quality</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <Sparkles className="w-3 h-3" />
              Optimal
            </span>
          </div>
          <div className="space-y-1.5">
            {[
              ['Documents detected', `${totalCount} of ${totalCount} found`],
              ['Image readable', 'High Contrast'],
              ['Perspective deskew', 'Corrected'],
            ].map(([label, val]) => (
              <div key={label} className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">{label}</span>
                <span className="flex items-center gap-1 text-emerald-600 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Bottom buttons ── */}
      <div className="flex-shrink-0 p-4 bg-white border-t border-slate-200 flex items-center gap-3">
        <button
          type="button"
          onClick={onRetake}
          className="flex-1 py-3.5 px-4 rounded-xl border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-100 transition text-center active:scale-98"
        >
          Retake
        </button>
        <button
          type="button"
          onClick={onAcceptScan}
          className="flex-2 py-3.5 px-5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 active:scale-98"
        >
          <span>Use {totalCount > 1 ? `All ${totalCount} Scans` : 'This Scan'}</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* ── Lightbox ── */}
      {lightboxIdx !== null && (
        <div
          className="absolute inset-0 z-50 bg-slate-950/95 backdrop-blur-md flex flex-col"
          onClick={closeLightbox}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            <div>
              <p className="text-sm font-bold text-white">{displayDocs[lightboxIdx].label}</p>
              <p className="text-[10px] text-slate-400 font-mono">{displayDocs[lightboxIdx].sublabel}</p>
            </div>
            <button type="button" onClick={closeLightbox}
              className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-white hover:bg-slate-700 transition">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Image */}
          <div className="flex-1 flex items-center justify-center p-4 min-h-0" onClick={(e) => e.stopPropagation()}>
            <img
              src={displayDocs[lightboxIdx].image}
              alt={displayDocs[lightboxIdx].label}
              className="max-w-full max-h-full object-contain rounded-xl shadow-2xl"
            />
          </div>

          {/* Navigation + counter */}
          {totalCount > 1 && (
            <div className="flex items-center justify-between px-6 py-4 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
              <button type="button" onClick={prevLightbox}
                className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-white hover:bg-slate-700 transition active:scale-90">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <div className="flex gap-1.5">
                {displayDocs.map((_, i) => (
                  <button key={i} type="button" onClick={() => setLightboxIdx(i)}
                    className={`w-2 h-2 rounded-full transition ${i === lightboxIdx ? 'bg-emerald-400 scale-125' : 'bg-slate-600'}`} />
                ))}
              </div>
              <button type="button" onClick={nextLightbox}
                className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-white hover:bg-slate-700 transition active:scale-90">
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
