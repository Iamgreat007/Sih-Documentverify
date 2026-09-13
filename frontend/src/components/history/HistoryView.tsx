"use client";
import React from 'react';
import { HistoryItem } from '@/types';
import { BookOpen, CreditCard, FileText, ChevronRight, ShieldCheck, Clock, CheckCircle2 } from 'lucide-react';

interface HistoryViewProps {
  history: HistoryItem[];
  onSelectRecord: (record: HistoryItem) => void;
  onStartNewScan: () => void;
}

export default function HistoryView({
  history,
  onSelectRecord,
  onStartNewScan,
}: HistoryViewProps) {
  const getDocIcon = (type: string) => {
    switch (type) {
      case 'passport':
        return <BookOpen className="w-5 h-5 text-blue-600" />;
      case 'aadhaar':
        return <CreditCard className="w-5 h-5 text-emerald-600" />;
      case 'visa':
      default:
        return <FileText className="w-5 h-5 text-teal-600" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 justify-between select-none">
      {/* Top Bar */}
      <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Scan History</h2>
          <p className="text-[10px] text-slate-500">Stored verification audits</p>
        </div>
        <span className="text-[11px] font-bold bg-slate-100 text-slate-600 px-2.5 py-0.5 rounded-full border border-slate-200">
          {history.length} scans
        </span>
      </div>

      {/* History Items List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {history.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6">
            <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
              <Clock className="w-6 h-6" />
            </div>
            <p className="text-sm font-bold text-slate-700">No scans yet</p>
            <p className="text-xs text-slate-400 mt-1">
              Captured documents will appear here with risk audits.
            </p>
          </div>
        ) : (
          history.map((item) => {
            const isLow = item.riskLevel === 'LOW';
            const isHigh = item.riskLevel === 'HIGH';

            return (
              <div
                key={item.id}
                onClick={() => onSelectRecord(item)}
                className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-xs hover:border-emerald-300 hover:shadow-sm transition-all cursor-pointer group active:scale-98"
              >
                <div className="flex items-start justify-between gap-3">
                  {/* Left Icon & Info */}
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center flex-shrink-0">
                      {getDocIcon(item.documentType)}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-extrabold text-slate-900 capitalize">
                          {item.documentType}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {item.identifier}
                        </span>
                      </div>

                      <div className="text-xs font-semibold text-slate-700 mt-0.5">
                        {item.holderName}
                      </div>

                      <div className="flex items-center gap-2 mt-2">
                        {/* Risk Tag */}
                        <span
                          className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                            isLow
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : isHigh
                              ? 'bg-rose-50 text-rose-700 border border-rose-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}
                        >
                          Risk: {item.riskLevel === 'LOW' ? 'Low' : item.riskLevel === 'HIGH' ? 'High' : 'Medium'}
                        </span>

                        {/* eKYC badge if verified */}
                        {item.ekycVerified && (
                          <span className="text-[10px] font-extrabold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <CheckCircle2 className="w-2.5 h-2.5" />
                            eKYC Verified
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right Arrow & Timestamp */}
                  <div className="flex flex-col items-end justify-between h-full">
                    <span className="text-[10px] font-medium text-slate-400">{item.timeAgo}</span>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 transition mt-4" />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Start New Scan Button */}
      <div className="p-4 bg-white border-t border-slate-200">
        <button
          type="button"
          onClick={onStartNewScan}
          className="w-full py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 active:scale-98"
        >
          <span>Start New Scan</span>
        </button>
      </div>
    </div>
  );
}
