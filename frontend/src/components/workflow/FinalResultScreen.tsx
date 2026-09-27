"use client";
import React, { useState } from 'react';
import { VerificationResult, DocumentType } from '@/types';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, ShieldAlert, FileText, ArrowRight } from 'lucide-react';

interface FinalResultScreenProps {
  documentType: DocumentType;
  fileName: string;
  initialResult: VerificationResult;
  onDone: () => void;
}

export default function FinalResultScreen({
  documentType,
  fileName,
  initialResult,
  onDone,
}: FinalResultScreenProps) {
  const [result, setResult] = useState<VerificationResult>(initialResult);

  const isAccepted = result.riskLevel === 'ACCEPTED';
  const isReviewRequired = result.riskLevel === 'REVIEW REQUIRED';
  const isFailed = result.riskLevel === 'FAILED';
  const isMissing = result.riskLevel === 'MISSING';

  const toggleSuspiciousDemo = () => {
    if (isAccepted) {
      setResult({
        riskLevel: 'REVIEW REQUIRED',
        riskScore: 78,
        explanation: 'Potential document alteration detected. Manual verification recommended.',
        checks: [
          {
            id: 'ocr',
            title: 'OCR Extraction',
            status: 'passed',
            detail: 'Demographic fields parsed successfully',
          },
          {
            id: 'tampering',
            title: 'Potential Tampering',
            status: 'warning',
            detail: 'Edge artifact & font discrepancy detected',
          },
          {
            id: 'face',
            title: 'Face Mismatch',
            status: 'warning',
            detail: 'Biometric similarity below threshold (42%)',
          },
          {
            id: 'mrz',
            title: 'Format Validation',
            status: 'passed',
            detail: 'Physical structure checksum passed',
          },
        ],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } else {
      setResult(initialResult);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 justify-between">
      <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded flex items-center justify-center border ${
              isAccepted
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : isReviewRequired
                ? 'bg-amber-50 border-amber-200 text-amber-700'
                : 'bg-rose-50 border-rose-200 text-rose-700'
            }`}
          >
            {isAccepted ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-900 block">Verification Result</span>
            <span className="text-[10px] text-slate-500 font-mono block truncate max-w-[120px]">{fileName}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={toggleSuspiciousDemo}
          className="text-[10px] font-medium px-2.5 py-1.5 rounded border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
        >
          {isAccepted ? 'Test Review State' : 'Reset'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-sm mx-auto w-full">
        <div className="bg-white rounded-lg p-5 border border-slate-200">
          <div className="mb-4">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
              System Assessment
            </span>
            <span
              className={`text-lg font-bold tracking-wide uppercase ${
                isAccepted
                  ? 'text-emerald-700'
                  : isReviewRequired
                  ? 'text-amber-700'
                  : 'text-rose-700'
              }`}
            >
              {result.riskLevel}
            </span>
          </div>

          <div className="mb-4 pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Risk Score
              </span>
              <span className="text-sm font-bold text-slate-700 font-mono">
                {result.riskScore} <span className="text-slate-400 font-normal">/ 100</span>
              </span>
            </div>
            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isAccepted
                    ? 'bg-emerald-600'
                    : isReviewRequired
                    ? 'bg-amber-500'
                    : 'bg-rose-600'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, result.riskScore))}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-50 rounded p-3 border border-slate-200 text-xs text-slate-700 leading-relaxed">
            {result.explanation}
          </div>
        </div>

        <div className="bg-white rounded-lg p-5 border border-slate-200">
          <div className="text-xs font-semibold text-slate-700 mb-4 pb-2 border-b border-slate-100">
            Verification Checks
          </div>

          <div className="space-y-3.5">
            {result.checks.map((check) => {
              const isPassed = check.status === 'passed';
              const isWarning = check.status === 'warning';

              return (
                <div key={check.id} className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {isPassed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : isWarning ? (
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <div className="text-xs font-medium text-slate-900 truncate">
                        {check.title}
                      </div>
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider flex-shrink-0 ${
                          isPassed
                            ? 'bg-emerald-50 text-emerald-700'
                            : isWarning
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-rose-50 text-rose-700'
                        }`}
                      >
                        {isPassed ? 'Pass' : isWarning ? 'Warn' : 'Fail'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 leading-snug">
                      {check.detail}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="p-4 bg-white border-t border-slate-200">
        <button
          type="button"
          onClick={onDone}
          className="w-full py-2.5 rounded-md bg-blue-700 text-white font-medium text-sm hover:bg-blue-800 transition flex items-center justify-center gap-2"
        >
          <span>Finish & Save</span>
          <CheckCircle2 className="w-4 h-4 text-blue-200" />
        </button>
      </div>
    </div>
  );
}
