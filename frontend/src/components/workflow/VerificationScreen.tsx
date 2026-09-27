"use client";
import React, { useState, useEffect } from 'react';
import { DocumentType } from '@/types';
import { CheckCircle2, Loader2, Hourglass, ShieldCheck } from 'lucide-react';

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
  const [stepIndex, setStepIndex] = useState<number>(1);

  useEffect(() => {
    const timer1 = setTimeout(() => setStepIndex(2), 600);
    const timer2 = setTimeout(() => setStepIndex(3), 1300);
    const timer3 = setTimeout(() => setStepIndex(4), 2100);
    const timer4 = setTimeout(() => {
      setStepIndex(5);
      setTimeout(() => onComplete(), 700);
    }, 2800);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
    };
  }, [onComplete]);

  const checks = [
    { id: 'ocr', label: 'OCR Extraction', thresholdStep: 1 },
    { id: 'doc', label: 'Format Validation', thresholdStep: 2 },
    { id: 'tamper', label: 'Tampering Detection', thresholdStep: 3 },
    { id: 'database', label: 'Database Verification', thresholdStep: 4 },
  ];

  const totalSteps = checks.length;
  const progressPct = Math.min(100, Math.round((stepIndex / totalSteps) * 100));

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 justify-between p-6 select-none">
      <div className="text-center pt-8">
        <div className="w-12 h-12 mx-auto rounded-lg bg-blue-50 border border-blue-100 text-blue-700 flex items-center justify-center mb-4">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">Verifying Document</h2>
        <p className="text-sm text-slate-500 mt-1">
          Running automated security checks
        </p>
      </div>

      <div className="w-full max-w-sm mx-auto bg-white rounded-lg p-5 border border-slate-200">
        <div className="mb-5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-600 mb-2">
            <span>Progress</span>
            <span className="font-mono text-blue-700 font-semibold">{progressPct}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-700 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="space-y-3">
          {checks.map((c) => {
            const isDone = stepIndex >= c.thresholdStep;
            const isInProgress = stepIndex === c.thresholdStep - 1;

            return (
              <div
                key={c.id}
                className="flex items-center justify-between py-1 transition-all duration-300"
              >
                <div className="flex items-center gap-3">
                  {isDone ? (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-blue-700" />
                    </div>
                  ) : isInProgress ? (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center">
                      <Hourglass className="w-3.5 h-3.5 text-slate-300" />
                    </div>
                  )}

                  <span
                    className={`text-sm transition-colors ${
                      isDone
                        ? 'text-slate-900 font-medium'
                        : isInProgress
                        ? 'text-blue-700 font-medium'
                        : 'text-slate-400'
                    }`}
                  >
                    {c.label}
                  </span>
                </div>

                <div className="text-xs">
                  {isDone ? (
                    <span className="text-blue-700 font-medium">Complete</span>
                  ) : isInProgress ? (
                    <span className="text-slate-600">Processing...</span>
                  ) : (
                    <span className="text-slate-300">Pending</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="text-center pb-4 border-t border-slate-200/50 pt-4 mt-6">
        <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
          System Processing
        </p>
      </div>
    </div>
  );
}
