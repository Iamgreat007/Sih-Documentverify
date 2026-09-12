"use client";
import React, { useState } from 'react';
import { Settings, Server, Shield, Smartphone, Sliders, CheckCircle2, RefreshCw } from 'lucide-react';

interface SettingsViewProps {
  onBackToScan: () => void;
}

export default function SettingsView({ onBackToScan }: SettingsViewProps) {
  const [apiUrl, setApiUrl] = useState<string>('http://localhost:8000');
  const [sensitivity, setSensitivity] = useState<'standard' | 'strict'>('standard');
  const [autoCrop, setAutoCrop] = useState<boolean>(true);
  const [testSaved, setTestSaved] = useState<boolean>(false);

  const handleSave = () => {
    setTestSaved(true);
    setTimeout(() => setTestSaved(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 text-slate-900 justify-between select-none">
      {/* Top Bar */}
      <div className="px-4 py-3 bg-white border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Settings</h2>
          <p className="text-[10px] text-slate-500">Scanner & API Configuration</p>
        </div>
        <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center">
          <Settings className="w-3.5 h-3.5 text-slate-600" />
        </div>
      </div>

      {/* Settings Form Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-sm mx-auto w-full">
        {/* Backend Model Integration Card */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-xs">
          <div className="flex items-center gap-2 mb-2">
            <Server className="w-4 h-4 text-emerald-600" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
              FastAPI AI Backend
            </h3>
          </div>
          <p className="text-xs text-slate-500 mb-3">
            Endpoint for future OCR, Face Verification, and Tampering models.
          </p>

          <label className="text-[11px] font-bold text-slate-500 block mb-1">
            Server API URL
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-slate-300 font-mono text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-[10px] text-slate-400">Default: http://localhost:8000</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Mock / Fallback Ready
            </span>
          </div>
        </div>

        {/* Security Strictness Mode */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-xs">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
              Verification Sensitivity
            </h3>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-3">
            <button
              type="button"
              onClick={() => setSensitivity('standard')}
              className={`p-3 rounded-xl text-left border transition ${
                sensitivity === 'standard'
                  ? 'border-emerald-500 bg-emerald-50/50 font-bold'
                  : 'border-slate-200 bg-white'
              }`}
            >
              <div className="text-xs font-bold text-slate-900">Standard</div>
              <div className="text-[10px] text-slate-500 mt-0.5">Balanced threshold</div>
            </button>

            <button
              type="button"
              onClick={() => setSensitivity('strict')}
              className={`p-3 rounded-xl text-left border transition ${
                sensitivity === 'strict'
                  ? 'border-emerald-500 bg-emerald-50/50 font-bold'
                  : 'border-slate-200 bg-white'
              }`}
            >
              <div className="text-xs font-bold text-slate-900">High Security</div>
              <div className="text-[10px] text-slate-500 mt-0.5">Zero tolerance</div>
            </button>
          </div>
        </div>

        {/* Camera Preferences */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200/90 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <Smartphone className="w-4 h-4 text-slate-700" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
              CamScanner Engine
            </h3>
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <div className="text-xs font-semibold text-slate-800">Auto Edge Detection</div>
              <div className="text-[10px] text-slate-400">
                Identify document corners on capture
              </div>
            </div>
            <input
              type="checkbox"
              checked={autoCrop}
              onChange={(e) => setAutoCrop(e.target.checked)}
              className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Bottom Save & Return Button */}
      <div className="p-4 bg-white border-t border-slate-200 flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          className="flex-1 py-3.5 rounded-xl border border-slate-300 text-slate-700 font-bold text-sm hover:bg-slate-100 transition text-center"
        >
          {testSaved ? 'Saved ✓' : 'Save Config'}
        </button>
        <button
          type="button"
          onClick={onBackToScan}
          className="flex-1 py-3.5 rounded-xl bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition text-center shadow-lg shadow-emerald-600/20 active:scale-98"
        >
          Return to Scan
        </button>
      </div>
    </div>
  );
}
