"use client";
import React, { useState } from 'react';
import { VerificationResult, DocumentType } from '@/types';
import { CheckCircle2, AlertTriangle, XCircle, ShieldCheck, ShieldAlert, Sparkles, ArrowRight } from 'lucide-react';

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

  const isLowRisk = result.riskLevel === 'LOW RISK';
  const isHighRisk = result.riskLevel === 'HIGH RISK';

  // Toggle for testing both Low Risk and High Risk scenarios in the demo
  const toggleSuspiciousDemo = () => {
    if (isLowRisk) {
      setResult({
        riskLevel: 'HIGH RISK',
        riskScore: 78,
        explanation:
          'Potential document alteration detected. Manual verification recommended.',
        checks: [
          {
            id: 'ocr',
            title: 'OCR extracted',
            status: 'passed',
            detail: 'Demographic fields parsed',
          },
          {
            id: 'tampering',
            title: 'Possible tampering detected',
            status: 'warning',
            detail: 'Edge artifact & font rasterization discrepancy detected',
          },
          {
            id: 'face',
            title: 'Face mismatch',
            status: 'warning',
            detail: 'Biometric photo similarity below threshold (42%)',
          },
          {
            id: 'mrz',
            title: 'MRZ valid',
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
      {/* Top Header */}
      <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded-lg flex items-center justify-center ${
              isLowRisk
                ? 'bg-emerald-100 text-emerald-600'
                : isHighRisk
                ? 'bg-rose-100 text-rose-600'
                : 'bg-amber-100 text-amber-600'
            }`}
          >
            {isLowRisk ? (
              <ShieldCheck className="w-4 h-4" />
            ) : (
              <ShieldAlert className="w-4 h-4" />
            )}
          </div>
          <div>
            <span className="text-xs font-bold text-slate-900">Verification Result</span>
            <span className="text-[10px] text-slate-400 block">{fileName}</span>
          </div>
        </div>

        {/* Demo Toggle to preview High / Low risk instantly */}
        <button
          type="button"
          onClick={toggleSuspiciousDemo}
          className="text-[10px] font-bold px-2 py-1 rounded-md border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 transition"
          title="Toggle suspicious scenario"
        >
          {isLowRisk ? 'Simulate High Risk' : 'Reset to Low Risk'}
        </button>
      </div>

      {/* Main Result Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-sm mx-auto w-full">
        {/* Large Result Status Card */}
        <div
          className={`rounded-3xl p-6 text-center border shadow-md transition-all ${
            isLowRisk
              ? 'bg-emerald-50/60 border-emerald-300 shadow-emerald-500/5'
              : isHighRisk
              ? 'bg-rose-50/70 border-rose-300 shadow-rose-500/5'
              : 'bg-amber-50/60 border-amber-300 shadow-amber-500/5'
          }`}
        >
          {/* Main Large Status Badge */}
          <div className="inline-block mb-3">
            <span
              className={`text-2xl font-black tracking-wider uppercase px-4 py-1.5 rounded-2xl inline-block ${
                isLowRisk
                  ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20'
                  : isHighRisk
                  ? 'bg-rose-600 text-white shadow-md shadow-rose-600/20'
                  : 'bg-amber-500 text-white shadow-md shadow-amber-500/20'
              }`}
            >
              {result.riskLevel}
            </span>
          </div>

          {/* Risk Score Display */}
          <div className="mb-3">
            <div className="text-[11px] font-extrabold uppercase tracking-widest text-slate-500">
              Risk Score
            </div>
            <div className="flex items-baseline justify-center gap-1 mt-0.5">
              <span
                className={`text-3xl font-black font-mono ${
                  isLowRisk
                    ? 'text-emerald-600'
                    : isHighRisk
                    ? 'text-rose-600'
                    : 'text-amber-600'
                }`}
              >
                {result.riskScore}
              </span>
              <span className="text-sm font-bold text-slate-400 font-mono">/ 100</span>
            </div>

            {/* Risk Gauge Bar */}
            <div className="w-48 mx-auto h-2 bg-slate-200/80 rounded-full mt-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isLowRisk
                    ? 'bg-emerald-500'
                    : isHighRisk
                    ? 'bg-rose-500'
                    : 'bg-amber-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(10, result.riskScore))}%` }}
              />
            </div>
          </div>

          {/* Short Explanation Box */}
          <div className="bg-white/90 rounded-2xl p-3 border border-slate-200/80 mt-4 text-xs font-medium text-slate-700 leading-relaxed shadow-xs">
            {result.explanation}
          </div>
        </div>

        {/* 3-4 Important Checks Card */}
        <div className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-xs">
          <div className="text-xs font-extrabold text-slate-500 uppercase tracking-wider mb-3">
            Security Verification Checks
          </div>

          <div className="space-y-3">
            {result.checks.map((check) => {
              const isPassed = check.status === 'passed';
              const isWarning = check.status === 'warning';

              return (
                <div
                  key={check.id}
                  className="flex items-start justify-between gap-2 py-1 border-b border-slate-100 last:border-0"
                >
                  <div className="flex items-start gap-2.5">
                    <div className="mt-0.5">
                      {isPassed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 fill-emerald-50" />
                      ) : isWarning ? (
                        <AlertTriangle className="w-4 h-4 text-amber-500 fill-amber-50" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-600 fill-rose-50" />
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">{check.title}</div>
                      <div className="text-[11px] text-slate-500">{check.detail}</div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap ${
                      isPassed
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : isWarning
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {isPassed ? 'Passed' : isWarning ? 'Warning' : 'Failed'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Main Button: Done */}
      <div className="p-4 bg-white border-t border-slate-200">
        <button
          type="button"
          onClick={onDone}
          className="w-full py-3.5 rounded-xl bg-slate-900 text-white font-bold text-sm hover:bg-slate-800 transition flex items-center justify-center gap-2 shadow-lg active:scale-98"
        >
          <span>Done</span>
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        </button>
      </div>
    </div>
  );
}
