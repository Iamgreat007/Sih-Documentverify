"use client";
import React, { useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
  Loader2,
  CreditCard,
  AlertTriangle,
  X,
  AlertCircle,
} from 'lucide-react';
import { verifyAadhaar } from '@/services/verificationService';
import { AadhaarEkycData } from '@/types';

interface AadhaarEkycScreenProps {
  maskedAadhaar?: string;
  onBack: () => void;
  onVerified: (ekycData: AadhaarEkycData) => void;
  onSkip: () => void;
}

export default function AadhaarEkycScreen({
  maskedAadhaar = 'XXXX XXXX 7821',
  onBack,
  onVerified,
  onSkip,
}: AadhaarEkycScreenProps) {
  const [isVerifying, setIsVerifying] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [ekycResult, setEkycResult] = useState<AadhaarEkycData | null>(null);
  const [showSkipModal, setShowSkipModal] = useState(false);

  const handleVerify = async () => {
    setIsVerifying(true);
    try {
      // Connects to clean verifyAadhaar service function
      const result = await verifyAadhaar(maskedAadhaar);
      setEkycResult(result);
      setIsVerified(true);
    } catch (err) {
      console.error('eKYC failed:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleProceed = () => {
    if (ekycResult) {
      onVerified(ekycResult);
    } else {
      onVerified({
        maskedAadhaar,
        nameVerified: true,
        dobVerified: true,
        genderVerified: true,
        isVerified: true,
        isSkipped: false,
      });
    }
  };

  return (
    <div className="relative flex flex-col h-full bg-slate-50 text-slate-900 justify-between">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
        <button
          type="button"
          onClick={onBack}
          className="p-1 -ml-1 text-slate-600 hover:text-slate-900 flex items-center gap-1 text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <div className="text-center">
          <h2 className="text-sm font-bold text-slate-900">Aadhaar eKYC</h2>
          <p className="text-[10px] text-slate-500">Identity Authentication</p>
        </div>
        {!isVerified ? (
          <button
            type="button"
            onClick={() => setShowSkipModal(true)}
            className="text-xs font-bold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 px-3 py-1 rounded-full transition active:scale-95 flex items-center gap-1"
          >
            <span>Skip</span>
          </button>
        ) : (
          <div className="w-10" />
        )}
      </div>

      {/* Main Card */}
      <div className="flex-1 overflow-y-auto p-5 flex flex-col justify-center max-w-sm mx-auto w-full">
        <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-md">
          {/* Card Icon */}
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4 border border-emerald-100">
            <CreditCard className="w-6 h-6" />
          </div>

          <h3 className="text-base font-extrabold text-slate-900">Aadhaar eKYC</h3>
          <p className="text-xs text-slate-500 mt-1 mb-5">
            Verify identity against demographic records
          </p>

          {/* Masked Aadhaar Box */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 mb-5 text-center">
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1">
              Aadhaar Number
            </span>
            <div className="font-mono text-xl font-black text-slate-900 tracking-widest">
              {maskedAadhaar}
            </div>
          </div>

          {/* Verification States */}
          {isVerified ? (
            <div className="space-y-3 mb-6 animate-in fade-in zoom-in-95 duration-300">
              <div className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                <span className="text-slate-700 font-semibold">Name</span>
                <span className="flex items-center gap-1 text-emerald-600 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Name verified
                </span>
              </div>

              <div className="flex items-center justify-between text-xs py-1 border-b border-slate-100">
                <span className="text-slate-700 font-semibold">Date of birth</span>
                <span className="flex items-center gap-1 text-emerald-600 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Date of birth verified
                </span>
              </div>

              <div className="flex items-center justify-between text-xs py-1">
                <span className="text-slate-700 font-semibold">Identity</span>
                <span className="flex items-center gap-1 text-emerald-600 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Identity verified
                </span>
              </div>

              {/* Large eKYC VERIFIED banner */}
              <div className="mt-4 bg-emerald-50 border-2 border-emerald-500 rounded-2xl p-3.5 text-center">
                <span className="text-xs font-bold text-emerald-700 block uppercase tracking-wider">
                  Result
                </span>
                <span className="text-base font-black text-emerald-600 tracking-wide">
                  eKYC VERIFIED ✓
                </span>
              </div>
            </div>
          ) : (
            <div className="mb-5">
              <button
                type="button"
                onClick={handleVerify}
                disabled={isVerifying}
                className="w-full py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 active:scale-98 disabled:opacity-60"
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Verifying Identity...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Verify Identity</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Non-mandatory notice & skip link if not verified */}
          {!isVerified && (
            <div className="mb-4 bg-amber-50/80 border border-amber-200/80 rounded-2xl p-3 text-left">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="text-[11px] text-amber-900 leading-tight">
                  <span className="font-bold">eKYC is not mandatory.</span> You can skip this step, but it will impact the overall verification score and risk factor.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowSkipModal(true)}
                className="mt-2 text-[11px] font-bold text-amber-700 hover:text-amber-800 underline underline-offset-2 flex items-center gap-1"
              >
                Skip eKYC verification →
              </button>
            </div>
          )}

          {/* Prototype Notice */}
          <p className="text-[10px] text-slate-400 text-center leading-relaxed">
            *Demo verification environment. Ready for UIDAI API authentication integration.
          </p>
        </div>
      </div>

      {/* Bottom Button */}
      <div className="p-4 bg-white border-t border-slate-200 space-y-2">
        <button
          type="button"
          onClick={isVerified ? handleProceed : handleVerify}
          className="w-full py-3.5 rounded-xl bg-slate-900 text-white font-bold text-sm hover:bg-slate-800 transition flex items-center justify-center gap-2 shadow-lg active:scale-98"
        >
          <span>{isVerified ? 'View Final Result' : 'Verify & Continue'}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        {!isVerified && (
          <button
            type="button"
            onClick={() => setShowSkipModal(true)}
            className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-amber-700 transition text-center"
          >
            Skip for now (Affects risk score)
          </button>
        )}
      </div>

      {/* Skip Confirmation Warning Modal / Popup */}
      {showSkipModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl p-6 border border-slate-200 max-w-sm w-full shadow-2xl space-y-4 animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-start justify-between">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shadow-xs">
                <AlertTriangle className="w-6 h-6 text-amber-600" />
              </div>
              <button
                type="button"
                onClick={() => setShowSkipModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h4 className="text-base font-black text-slate-900">Skip Aadhaar eKYC?</h4>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Aadhaar eKYC is not mandatory, but skipping this step <span className="font-bold text-slate-700">will directly affect your overall score and risk factor</span>.
              </p>
            </div>

            {/* Impact Details Callout */}
            <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-3.5 space-y-2 text-left">
              <div className="flex items-center gap-1.5 text-[11px] font-bold text-amber-900 uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span>Expected Impact</span>
              </div>

              <div className="space-y-2 text-xs text-slate-700">
                <div className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold shrink-0">⚠️</span>
                  <span>
                    <strong className="text-slate-900">Risk Factor Elevated:</strong> Overall rating shifts to <strong className="text-amber-700 font-extrabold">MEDIUM RISK</strong> due to unverified demographic records.
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold shrink-0">📈</span>
                  <span>
                    <strong className="text-slate-900">Score Penalty:</strong> Increases risk score by <strong className="text-amber-700 font-bold">+20%</strong> for unauthenticated identity.
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold shrink-0">📋</span>
                  <span>
                    <strong className="text-slate-900">Audit Check:</strong> Security summary will log a warning item <em>&quot;Aadhaar eKYC skipped&quot;</em>.
                  </span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowSkipModal(false);
                  onSkip();
                }}
                className="w-full py-3.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs transition active:scale-98 shadow-md shadow-amber-600/20 flex items-center justify-center gap-2"
              >
                <span>Skip Anyway &amp; Accept Penalty</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={() => setShowSkipModal(false)}
                className="w-full py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold text-xs transition active:scale-98"
              >
                Cancel &amp; Verify Identity
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
