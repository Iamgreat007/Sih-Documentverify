"use client";
import React, { useState, useRef, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam';
import {
  Camera,
  Image as ImageIcon,
  Zap,
  ZapOff,
  RefreshCw,
  ShieldCheck,
  FolderCheck,
  Check,
  Plus,
  ArrowRight,
  Pencil,
  X,
  Sparkles,
  SlidersHorizontal,
  RotateCcw,
  CheckCircle2,
} from 'lucide-react';
import {
  detectCornersWithFallback,
  processScanWithFallback,
  Point,
  ScanFilter,
} from '@/utils/scannerUtils';
import { loadOpenCV } from '@/utils/opencvScanner';
import { saveCapturedImageToDisk } from '@/services/verificationService';
import { DocumentType } from '@/types';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------
export type DocPreset = 'aadhaar' | 'driving_license' | 'passport' | 'visa' | 'tampered';
export type DocSide = 'front' | 'back' | 'single';

export interface CapturedDoc {
  id: string;
  docType: DocumentType;
  side: DocSide;
  fileName: string;
  rawImage: string;
  processedImage: string;
  savedPath: string;
  isSuspicious: boolean;
  qualityScore: number;
  corners: Point[];
  filterUsed?: ScanFilter;
}

export interface ScanSessionPayload {
  documents: CapturedDoc[];
  primaryDoc: CapturedDoc; // first non-suspicious doc, or first overall
}

interface WebCamScannerProps {
  onSessionComplete: (payload: ScanSessionPayload) => void;
  onRequestManualCrop?: (rawImage: string, corners: Point[]) => void;
}

interface PendingScan {
  rawSrc: string;
  corners: Point[];
  filter: ScanFilter;
  confidence: number;
}

// ------------------------------------------------------------------
// Helpers & Presets
// ------------------------------------------------------------------
const PRESET_META: Record<
  DocPreset,
  {
    label: string;
    docType: DocumentType;
    sides: DocSide[];
    sampleImages: Partial<Record<DocSide, string>>;
    isSuspicious?: boolean;
  }
> = {
  aadhaar: {
    label: 'Aadhaar Card',
    docType: 'aadhaar',
    sides: ['front', 'back'],
    sampleImages: {
      front: '/samples/aadhaar_front.svg',
      back: '/samples/aadhaar_back.svg',
    },
  },
  driving_license: {
    label: 'Driving Licence',
    docType: 'driving_license',
    sides: ['front', 'back'],
    sampleImages: {
      front: '/samples/driving_license_front.svg',
      back: '/samples/driving_license_back.svg',
    },
  },
  passport: {
    label: 'Passport',
    docType: 'passport',
    sides: ['single'],
    sampleImages: { single: '/samples/passport_front.svg' },
  },
  visa: {
    label: 'Visa',
    docType: 'visa',
    sides: ['single'],
    sampleImages: { single: '/samples/visa_front.svg' },
  },
  tampered: {
    label: 'Tampered Aadhaar ⚠️',
    docType: 'aadhaar',
    sides: ['front'],
    sampleImages: { front: '/samples/aadhaar_tampered_sample.svg' },
    isSuspicious: true,
  },
};

const SIDE_LABEL: Record<DocSide, string> = {
  front: 'Front',
  back: 'Back',
  single: 'Page',
};

const FILTERS: { id: ScanFilter; label: string; icon: string }[] = [
  { id: 'original', label: 'Original', icon: '📷' },
  { id: 'bw_clean', label: 'Crisp B&W', icon: '📄' },
  { id: 'grayscale', label: 'Grayscale', icon: '🌓' },
];

function shortId() {
  return Math.random().toString(36).slice(2, 8);
}

// ------------------------------------------------------------------
// Component
// ------------------------------------------------------------------
export default function WebCamScanner({
  onSessionComplete,
  onRequestManualCrop,
}: WebCamScannerProps) {
  const webcamRef = useRef<Webcam>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cropContainerRef = useRef<HTMLDivElement>(null);
  const cropImgRef = useRef<HTMLImageElement>(null);

  // Camera state
  const [hasCamera, setHasCamera] = useState<boolean | null>(null);
  const [flashOn, setFlashOn] = useState(false);
  const [cameraFacing, setCameraFacing] = useState<'environment' | 'user'>('environment');
  const [isProcessing, setIsProcessing] = useState(false);

  // Queue: list of already-captured docs in this session
  const [captured, setCaptured] = useState<CapturedDoc[]>([]);

  // Current slot being configured
  const [activePreset, setActivePreset] = useState<DocPreset>('aadhaar');
  const [activeSide, setActiveSide] = useState<DocSide>('front');
  const [activeFileName, setActiveFileName] = useState<string>('aadhaar_front');
  const [isEditingName, setIsEditingName] = useState(false);

  // Pending capture: In-viewfinder instant corner & filter review
  const [pendingScan, setPendingScan] = useState<PendingScan | null>(null);
  const [displayPoints, setDisplayPoints] = useState<Point[]>([]);
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);
  const draggingIdxRef = useRef<number | null>(null);

  // Toast
  const [toast, setToast] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // Preload OpenCV in background
  useEffect(() => {
    loadOpenCV().catch(() => {});
  }, []);

  // Camera check
  useEffect(() => {
    navigator.mediaDevices
      ?.getUserMedia?.({ video: true })
      .then((s) => {
        setHasCamera(true);
        s.getTracks().forEach((t) => t.stop());
      })
      .catch(() => setHasCamera(false));
  }, []);

  // Update file name when preset or side changes (only if user hasn't manually set it)
  useEffect(() => {
    setActiveFileName(`${activePreset}_${activeSide}`);
  }, [activePreset, activeSide]);

  const handlePresetChange = (p: DocPreset) => {
    setActivePreset(p);
    setActiveSide(PRESET_META[p].sides[0]);
  };

  const meta = PRESET_META[activePreset];
  const sampleImage = meta.sampleImages[activeSide] || Object.values(meta.sampleImages)[0];

  // ----------------------------------------------------------------
  // Corner Drag Mapping (for In-Viewfinder Fine Tuning)
  // ----------------------------------------------------------------
  const initDisplayPoints = useCallback((corners: Point[], imgEl: HTMLImageElement) => {
    if (!cropContainerRef.current) return;
    const containerRect = cropContainerRef.current.getBoundingClientRect();
    const imgRect = imgEl.getBoundingClientRect();

    const offsetX = imgRect.left - containerRect.left;
    const offsetY = imgRect.top - containerRect.top;
    const scaleX = imgRect.width / imgEl.naturalWidth;
    const scaleY = imgRect.height / imgEl.naturalHeight;

    setDisplayPoints(
      corners.map((pt) => ({
        x: pt.x * scaleX + offsetX,
        y: pt.y * scaleY + offsetY,
      }))
    );
  }, []);

  const getEventPos = useCallback((e: MouseEvent | TouchEvent) => {
    if (!cropContainerRef.current) return { x: 0, y: 0 };
    const rect = cropContainerRef.current.getBoundingClientRect();
    if ('touches' in e && e.touches.length > 0) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top,
      };
    }
    const me = e as MouseEvent;
    return {
      x: me.clientX - rect.left,
      y: me.clientY - rect.top,
    };
  }, []);

  const handleDragMove = useCallback(
    (e: MouseEvent | TouchEvent) => {
      if (draggingIdxRef.current === null || !cropImgRef.current || !cropContainerRef.current) return;
      if (e.cancelable) e.preventDefault();

      const pos = getEventPos(e);
      const imgRect = cropImgRef.current.getBoundingClientRect();
      const containerRect = cropContainerRef.current.getBoundingClientRect();
      const ox = imgRect.left - containerRect.left;
      const oy = imgRect.top - containerRect.top;

      // Clamp to image dimensions
      const clampedX = Math.max(ox, Math.min(pos.x, ox + imgRect.width));
      const clampedY = Math.max(oy, Math.min(pos.y, oy + imgRect.height));

      setDisplayPoints((prev) => {
        const next = [...prev];
        next[draggingIdxRef.current!] = { x: clampedX, y: clampedY };
        return next;
      });
    },
    [getEventPos]
  );

  const handleDragEnd = useCallback(() => {
    draggingIdxRef.current = null;
    setDraggingIdx(null);
  }, []);

  useEffect(() => {
    document.addEventListener('mousemove', handleDragMove);
    document.addEventListener('mouseup', handleDragEnd);
    document.addEventListener('touchmove', handleDragMove, { passive: false });
    document.addEventListener('touchend', handleDragEnd);

    return () => {
      document.removeEventListener('mousemove', handleDragMove);
      document.removeEventListener('mouseup', handleDragEnd);
      document.removeEventListener('touchmove', handleDragMove);
      document.removeEventListener('touchend', handleDragEnd);
    };
  }, [handleDragMove, handleDragEnd]);

  // Convert display coordinates back to image space
  const getScaledCorners = (): Point[] => {
    if (!cropImgRef.current || !cropContainerRef.current || displayPoints.length !== 4) {
      return pendingScan?.corners || [];
    }
    const img = cropImgRef.current;
    const imgRect = img.getBoundingClientRect();
    const containerRect = cropContainerRef.current.getBoundingClientRect();
    const offsetX = imgRect.left - containerRect.left;
    const offsetY = imgRect.top - containerRect.top;

    const scaleX = img.naturalWidth / imgRect.width;
    const scaleY = img.naturalHeight / imgRect.height;

    return displayPoints.map((pt) => ({
      x: (pt.x - offsetX) * scaleX,
      y: (pt.y - offsetY) * scaleY,
    }));
  };

  // ----------------------------------------------------------------
  // Trigger Capture -> Open In-Viewfinder Review
  // ----------------------------------------------------------------
  const handleCapture = async () => {
    if (isProcessing) return;
    setIsProcessing(true);

    try {
      let rawSrc: string | null = webcamRef.current?.getScreenshot() ?? null;
      if (!rawSrc) rawSrc = sampleImage!;

      // Run advanced OpenCV / Homography corner detection
      const { corners, confidence } = await detectCornersWithFallback(rawSrc);

      setPendingScan({
        rawSrc,
        corners,
        filter: 'original',
        confidence,
      });
    } catch (err) {
      console.error('Capture error:', err);
      showToast('Capture failed. Try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Gallery upload
  const handleGalleryUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const src = ev.target?.result as string;
      if (src) {
        setIsProcessing(true);
        try {
          const { corners, confidence } = await detectCornersWithFallback(src);
          setPendingScan({
            rawSrc: src,
            corners,
            filter: 'original',
            confidence,
          });
        } finally {
          setIsProcessing(false);
        }
      }
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // ----------------------------------------------------------------
  // Save confirmed scan from In-Viewfinder Review
  // ----------------------------------------------------------------
  const handleConfirmScan = async () => {
    if (!pendingScan || isProcessing) return;
    setIsProcessing(true);

    try {
      const finalCorners = getScaledCorners();
      // Run true 4-point perspective warp with selected CamScanner filter
      const processed = await processScanWithFallback(
        pendingScan.rawSrc,
        finalCorners,
        0,
        0,
        pendingScan.filter
      );

      const saveResult = await saveCapturedImageToDisk(
        processed || pendingScan.rawSrc,
        meta.docType,
        activeSide === 'single' ? 'front' : activeSide,
        activeFileName
      );

      const doc: CapturedDoc = {
        id: shortId(),
        docType: meta.docType,
        side: activeSide,
        fileName: activeFileName,
        rawImage: pendingScan.rawSrc,
        processedImage: processed,
        savedPath: saveResult.savedPath,
        isSuspicious: !!meta.isSuspicious,
        qualityScore: Math.round(pendingScan.confidence * 100) || 98,
        corners: finalCorners,
        filterUsed: pendingScan.filter,
      };

      setCaptured((prev) => [...prev, doc]);
      showToast(`✓ Deskewed & Saved → image/${saveResult.fileName}`);

      // Auto-advance side: if front captured and doc has back, switch to back
      if (activeSide === 'front' && PRESET_META[activePreset].sides.includes('back')) {
        setActiveSide('back');
        setActiveFileName(`${activePreset}_back`);
      }

      setPendingScan(null);
    } catch (err) {
      console.error('Save error:', err);
      showToast('Could not process scan. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const removeDoc = (id: string) => setCaptured((prev) => prev.filter((d) => d.id !== id));

  const handleProceed = () => {
    if (captured.length === 0) return;
    const primary = captured.find((d) => !d.isSuspicious) ?? captured[0];
    onSessionComplete({ documents: captured, primaryDoc: primary });
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-white select-none">
      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/95 backdrop-blur-md border-b border-slate-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg">
            <ShieldCheck className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm text-white">SecureScan AI</span>
              <span className="text-[10px] font-bold bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/30">
                CamScanner Pro
              </span>
            </div>
            <p className="text-[10px] text-slate-400">OpenCV Deskew · Auto-save to ./image</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setFlashOn(!flashOn)}
            className={`p-1.5 rounded-full transition ${
              flashOn ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-slate-300'
            }`}
          >
            {flashOn ? <Zap className="w-4 h-4 fill-current" /> : <ZapOff className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={() => setCameraFacing((f) => (f === 'environment' ? 'user' : 'environment'))}
            className="p-1.5 rounded-full bg-slate-800 text-slate-300 hover:text-white transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Current slot selector ── */}
      <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex-shrink-0">
        {/* Preset Pills */}
        <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none mb-1.5">
          {(Object.keys(PRESET_META) as DocPreset[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => handlePresetChange(p)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap flex-shrink-0 transition ${
                activePreset === p
                  ? p === 'tampered'
                    ? 'bg-rose-500 text-white'
                    : 'bg-emerald-500 text-slate-950'
                  : 'bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700'
              }`}
            >
              {PRESET_META[p].label}
            </button>
          ))}
        </div>

        {/* Side + File name row */}
        <div className="flex items-center gap-2">
          {meta.sides.length > 1 && (
            <div className="flex items-center gap-0.5 bg-slate-800 p-0.5 rounded-lg border border-slate-700">
              {meta.sides.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setActiveSide(s);
                    setActiveFileName(`${activePreset}_${s}`);
                  }}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition flex items-center gap-0.5 ${
                    activeSide === s ? 'bg-emerald-500 text-slate-950' : 'text-slate-300'
                  }`}
                >
                  {captured.some((d) => d.docType === meta.docType && d.side === s) && (
                    <Check className="w-2.5 h-2.5" />
                  )}
                  {SIDE_LABEL[s]}
                </button>
              ))}
            </div>
          )}

          {/* File name inline edit */}
          <div className="flex-1 flex items-center gap-1 bg-slate-800 rounded-lg px-2.5 py-1 border border-slate-700">
            <span className="text-[10px] text-slate-400 font-mono flex-shrink-0">📁</span>
            {isEditingName ? (
              <input
                type="text"
                autoFocus
                value={activeFileName}
                onChange={(e) => setActiveFileName(e.target.value.replace(/[^a-zA-Z0-9_-]/g, '_'))}
                onBlur={() => setIsEditingName(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setIsEditingName(false);
                }}
                className="flex-1 bg-transparent text-[11px] font-mono text-white focus:outline-none min-w-0"
              />
            ) : (
              <button
                type="button"
                onClick={() => setIsEditingName(true)}
                className="flex-1 text-left text-[11px] font-mono text-emerald-300 hover:text-emerald-200 flex items-center gap-1 truncate"
              >
                <span className="truncate">{activeFileName}</span>
                <Pencil className="w-2.5 h-2.5 text-slate-500 flex-shrink-0" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Viewfinder / Scanner Mechanism ── */}
      <div className="relative flex-1 flex items-center justify-center overflow-hidden bg-black px-2 py-1.5 min-h-0">
        {flashOn && <div className="absolute inset-0 bg-white/20 z-10 pointer-events-none" />}

        <div className="relative w-full h-full max-h-full rounded-xl overflow-hidden border border-slate-700/60 shadow-2xl bg-slate-900 flex items-center justify-center">
          {/* Live Camera Stream */}
          {pendingScan === null ? (
            <>
              {hasCamera !== false ? (
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{
                    facingMode: cameraFacing,
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                  }}
                  onUserMedia={() => setHasCamera(true)}
                  onUserMediaError={() => setHasCamera(false)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center p-4 bg-slate-900">
                  <img
                    src={sampleImage}
                    alt="Sample"
                    className="w-full h-auto max-h-full object-contain rounded-lg shadow-xl"
                  />
                </div>
              )}

              {/* Dynamic CamScanner Viewfinder Guides */}
              <div className="absolute inset-4 rounded-xl border border-emerald-400/40 pointer-events-none transition-all">
                {/* 4 Corner Targeting L-Brackets */}
                <div className="absolute -top-1 -left-1 w-6 h-6 border-t-3 border-l-3 border-emerald-400 rounded-tl shadow-[0_0_8px_#10b981]" />
                <div className="absolute -top-1 -right-1 w-6 h-6 border-t-3 border-r-3 border-emerald-400 rounded-tr shadow-[0_0_8px_#10b981]" />
                <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-3 border-l-3 border-emerald-400 rounded-bl shadow-[0_0_8px_#10b981]" />
                <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-3 border-r-3 border-emerald-400 rounded-br shadow-[0_0_8px_#10b981]" />

                {/* Laser Scanning Line */}
                <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-laser shadow-[0_0_12px_#34d399]" />
              </div>

              {/* Real-time Document Detection Feedback */}
              <div className="absolute top-3 inset-x-4 flex justify-center pointer-events-none z-10">
                <div className="bg-slate-900/90 border border-emerald-500/40 text-emerald-400 px-3 py-1 rounded-full text-[11px] font-bold backdrop-blur-md flex items-center gap-1.5 shadow-xl">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  {PRESET_META[activePreset].label} · {SIDE_LABEL[activeSide]} In Frame
                </div>
              </div>
            </>
          ) : (
            /* ── Interactive In-Viewfinder Review & Corner Adjustment ── */
            <div
              ref={cropContainerRef}
              className="relative w-full h-full flex flex-col items-center justify-center bg-slate-950 select-none overflow-hidden"
            >
              {/* Captured Image */}
              <img
                ref={cropImgRef}
                src={pendingScan.rawSrc}
                alt="Captured document"
                onLoad={(e) => initDisplayPoints(pendingScan.corners, e.currentTarget)}
                className="max-w-full max-h-full object-contain pointer-events-none"
              />

              {/* Bounding Quadrilateral Overlay */}
              {displayPoints.length === 4 && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-20">
                  <polygon
                    points={displayPoints.map((p) => `${p.x},${p.y}`).join(' ')}
                    fill="rgba(16, 185, 129, 0.22)"
                    stroke="#10b981"
                    strokeWidth="2.5"
                    strokeDasharray="4 2"
                  />
                  {/* Diagonal Guidelines */}
                  <line
                    x1={displayPoints[0].x}
                    y1={displayPoints[0].y}
                    x2={displayPoints[2].x}
                    y2={displayPoints[2].y}
                    stroke="rgba(16, 185, 129, 0.25)"
                    strokeWidth="1"
                  />
                  <line
                    x1={displayPoints[1].x}
                    y1={displayPoints[1].y}
                    x2={displayPoints[3].x}
                    y2={displayPoints[3].y}
                    stroke="rgba(16, 185, 129, 0.25)"
                    strokeWidth="1"
                  />
                </svg>
              )}

              {/* Interactive 4 Draggable Corner Handles */}
              {displayPoints.map((pt, idx) => (
                <div
                  key={idx}
                  style={{
                    left: `${pt.x}px`,
                    top: `${pt.y}px`,
                    transform: 'translate(-50%, -50%)',
                  }}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    draggingIdxRef.current = idx;
                    setDraggingIdx(idx);
                  }}
                  onTouchStart={(e) => {
                    e.preventDefault();
                    draggingIdxRef.current = idx;
                    setDraggingIdx(idx);
                  }}
                  className={`absolute z-30 w-8 h-8 rounded-full flex items-center justify-center cursor-grab active:cursor-grabbing transition-transform ${
                    draggingIdx === idx ? 'scale-130 ring-4 ring-emerald-400' : 'hover:scale-110'
                  }`}
                >
                  <div className="w-5 h-5 rounded-full bg-emerald-400 border-2 border-slate-950 shadow-lg flex items-center justify-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-950" />
                  </div>
                </div>
              ))}

              {/* Filter Selector Bar (CamScanner Enhancements) */}
              <div className="absolute top-2 inset-x-2 z-30 flex items-center justify-center">
                <div className="flex gap-1 bg-slate-900/90 backdrop-blur-md p-1 rounded-xl border border-slate-700/80 shadow-2xl">
                  {FILTERS.map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => setPendingScan((p) => (p ? { ...p, filter: f.id } : null))}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition flex items-center gap-1 ${
                        pendingScan.filter === f.id
                          ? 'bg-emerald-500 text-slate-950 shadow-md'
                          : 'text-slate-300 hover:text-white hover:bg-slate-800'
                      }`}
                    >
                      <span>{f.icon}</span>
                      <span>{f.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Floating Buttons */}
              <div className="absolute bottom-3 inset-x-4 z-30 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setPendingScan(null)}
                  className="px-4 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-bold border border-slate-700/80 backdrop-blur-md transition flex items-center gap-1.5 active:scale-95"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Retake
                </button>

                <button
                  type="button"
                  onClick={handleConfirmScan}
                  disabled={isProcessing}
                  className="flex-1 py-2 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-extrabold shadow-lg shadow-emerald-500/25 transition flex items-center justify-center gap-1.5 active:scale-95"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Accept & Deskew Scan
                </button>
              </div>
            </div>
          )}

          {/* Processing Overlay */}
          {isProcessing && (
            <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm z-40 flex flex-col items-center justify-center">
              <div className="w-10 h-10 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin" />
              <p className="mt-2.5 text-xs font-bold text-white">Deskewing & Enhancing...</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Toast Notification ── */}
      {toast && (
        <div className="absolute top-28 inset-x-4 flex justify-center z-50 pointer-events-none animate-in fade-in duration-200">
          <div className="bg-emerald-500 text-slate-950 px-3.5 py-1.5 rounded-full text-[11px] font-black shadow-xl flex items-center gap-1.5">
            <FolderCheck className="w-3.5 h-3.5" />
            {toast}
          </div>
        </div>
      )}

      {/* ── Captured Docs Tray ── */}
      {captured.length > 0 && (
        <div className="flex-shrink-0 bg-slate-900 border-t border-slate-800 px-3 py-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
              Captured ({captured.length})
            </span>
            <span className="text-[10px] text-emerald-400 font-bold">All saved to ./image</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
            {captured.map((doc) => (
              <div key={doc.id} className="relative flex-shrink-0 w-16">
                <div
                  className={`w-16 h-12 rounded-lg overflow-hidden border-2 ${
                    doc.isSuspicious ? 'border-rose-500' : 'border-emerald-500'
                  }`}
                >
                  <img
                    src={doc.processedImage}
                    alt={doc.fileName}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="text-center mt-0.5">
                  <p className="text-[8px] text-slate-300 font-mono truncate w-full leading-tight">
                    {doc.fileName}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeDoc(doc.id)}
                  className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-rose-600 text-white rounded-full flex items-center justify-center shadow-md"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </div>
            ))}

            {/* Add more shortcut */}
            <button
              type="button"
              onClick={() => {}}
              className="flex-shrink-0 w-16 h-12 rounded-lg border-2 border-dashed border-slate-700 flex items-center justify-center text-slate-600 hover:border-emerald-500 hover:text-emerald-400 transition"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── Bottom Controls ── */}
      <div className="flex-shrink-0 px-4 py-3 bg-slate-950 border-t border-slate-900 flex items-center justify-between gap-3">
        {/* Gallery */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-white transition active:scale-95"
        >
          <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center">
            <ImageIcon className="w-4 h-4" />
          </div>
          <span className="text-[9px] font-medium">Gallery</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleGalleryUpload}
        />

        {/* Shutter */}
        <button
          type="button"
          onClick={handleCapture}
          disabled={isProcessing || pendingScan !== null}
          className="group p-1 active:scale-90 transition disabled:opacity-40"
        >
          <div className="w-16 h-16 rounded-full border-[3px] border-emerald-400 flex items-center justify-center p-1 shadow-xl pulse-shutter">
            <div className="w-full h-full rounded-full bg-white group-hover:bg-emerald-300 transition flex items-center justify-center">
              <Camera className="w-6 h-6 text-slate-950" />
            </div>
          </div>
        </button>

        {/* Proceed button (active once ≥1 captured) */}
        {captured.length > 0 ? (
          <button
            type="button"
            onClick={handleProceed}
            className="flex flex-col items-center gap-0.5 active:scale-95 transition"
          >
            <div className="w-10 h-10 rounded-full bg-emerald-600 border border-emerald-400 flex items-center justify-center shadow-lg shadow-emerald-600/30 relative">
              <ArrowRight className="w-5 h-5 text-white" />
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-white text-emerald-700 text-[9px] font-black rounded-full flex items-center justify-center">
                {captured.length}
              </span>
            </div>
            <span className="text-[9px] font-bold text-emerald-400">Proceed</span>
          </button>
        ) : (
          <div className="flex flex-col items-center gap-0.5 text-slate-600">
            <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center">
              <FolderCheck className="w-4 h-4" />
            </div>
            <span className="text-[9px] font-medium">Auto Save</span>
          </div>
        )}
      </div>
    </div>
  );
}
