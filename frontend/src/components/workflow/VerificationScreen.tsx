"use client";
import React, { useState, useEffect } from 'react';
import { DocumentType } from '@/types';
import { CheckCircle2, Loader2, Hourglass, ShieldCheck, Sparkles } from 'lucide-react';

interface VerificationScreenProps {
  documentType: DocumentType;
  isSuspicious?: boolean;
  onComplete: () => void;
}

export default function VerificationScreen({
  documentType,
  isSuspicious = false,
  onComplete,
}: VerificationScreenProps) {
  // Step sequence: 0 = starting, 1 = OCR, 2 = Doc validation, 3 = Tampering, 4 = Face, 5 = Aadhaar eKYC (if applicable), 6 = Complete
  const [stepIndex, setStepIndex] = useState<number>(1);

  const isAadhaar = documentType === 'aadhaar';

  useEffect(() => {
    const timer1 = setTimeout(() => setStepIndex(2), 600);
    const timer2 = setTimeout(() => setStepIndex(3), 1300);
    const timer3 = setTimeout(() => setStepIndex(4), 2100);
    const timer4 = setTimeout(() => {
      if (isAadhaar) {
        setStepIndex(5);
        // Aadhaar has its own eKYC interactive screen next!
        setTimeout(() => onComplete(), 700);
      } else {
        setStepIndex(5);
        setTimeout(() => onComplete(), 700);
      }
    }, 2800);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
    };
  }, [isAadhaar, onComplete]);

  const checks = [
    {
      id: 'ocr',
      label: 'OCR Extraction',
      thresholdStep: 1,
    },
    {
      id: 'doc',
      label: 'Document Validation',
      thresholdStep: 2,
    },
    {
      id: 'tamper',
      label: 'Tampering Detection',
      thresholdStep: 3,
    },
    {
      id: 'face',
      label: 'Face Verification',
      thresholdStep: 4,
    },
  ];

  if (isAadhaar) {
    checks.push({
      id: 'ekyc',
      label: 'Aadhaar eKYC',
      thresholdStep: 5,
    });
  }

  // Progress percentage calculation
  const totalSteps = checks.length;
  const progressPct = Math.min(100, Math.round((stepIndex / totalSteps) * 100));

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 justify-between p-6 select-none">
      {/* Top Header */}
      <div className="text-center pt-6">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center mb-3 shadow-inner">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">AI Verification</h2>
        <p className="text-xs text-slate-500 mt-1">
          Running automated security & forensic checks
        </p>
      </div>

      {/* Main Checklist Card */}
      <div className="w-full max-w-sm mx-auto bg-white rounded-3xl p-6 border border-slate-200/90 shadow-lg shadow-slate-100">
        {/* Subtle Animated Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600 mb-1.5">
            <span>Analyzing document</span>
            <span className="font-mono text-emerald-600 font-bold">{progressPct}%</span>
          </div>
          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* The 4-5 core checks as specified in requirements */}
        <div className="space-y-4">
          {checks.map((c) => {
            const isDone = stepIndex >= c.thresholdStep;
            const isInProgress = stepIndex === c.thresholdStep - 1;

            return (
              <div
                key={c.id}
                className="flex items-center justify-between py-1.5 transition-all duration-300"
              >
                <div className="flex items-center gap-3">
                  {isDone ? (
                    <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center animate-in zoom-in duration-200">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    </div>
                  ) : isInProgress ? (
                    <div className="w-6 h-6 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center">
                      <Loader2 className="w-4 h-4 animate-spin text-amber-500" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center">
                      <Hourglass className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  )}

                  <span
                    className={`text-sm font-semibold transition-colors ${
                      isDone
                        ? 'text-slate-900 font-bold'
                        : isInProgress
                        ? 'text-emerald-700'
                        : 'text-slate-400'
                    }`}
                  >
                    {c.label}
                  </span>
                </div>

                {/* Status symbol indicator */}
                <div className="text-xs font-medium">
                  {isDone ? (
                    <span className="text-emerald-600 font-bold">✓ Complete</span>
                  ) : isInProgress ? (
                    <span className="text-amber-500 animate-pulse font-mono">Running...</span>
                  ) : (
                    <span className="text-slate-300 font-mono">⏳ Queued</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom status note */}
      <div className="text-center pb-4">
        <p className="text-[11px] text-slate-400 font-medium">
          SecureScan AI Engine • Encrypted processing
        </p>
      </div>
    </div>
  );
}
