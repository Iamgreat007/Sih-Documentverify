"use client";
import React from 'react';
import ManualCrop from '@/components/ManualCrop';
import { ArrowLeft, Check, RotateCcw } from 'lucide-react';
import { Point } from '@/utils/scannerUtils';

interface ManualCropWrapperProps {
  imageSrc: string;
  initialCorners?: Point[];
  onConfirmCrop: (data: { points: Point[]; horizontalTilt: number; verticalTilt: number }) => void;
  onCancel: () => void;
}

export default function ManualCropWrapper({
  imageSrc,
  initialCorners,
  onConfirmCrop,
  onCancel,
}: ManualCropWrapperProps) {
  return (
    <div className="flex flex-col h-full bg-slate-950 text-white select-none">
      {/* Top Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
        <button
          type="button"
          onClick={onCancel}
          className="p-2 -ml-2 rounded-full text-slate-300 hover:text-white transition flex items-center gap-1.5"
        >
          <ArrowLeft className="w-5 h-5" />
          <span className="text-xs font-semibold">Back</span>
        </button>
        <div className="text-center">
          <h3 className="text-sm font-bold text-white">Adjust Corners</h3>
          <p className="text-[10px] text-slate-400">Drag 4 corners to document boundary</p>
        </div>
        <div className="w-8" />
      </div>

      {/* Manual Crop Body */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col items-center justify-start">
        <ManualCrop
          imageSrc={imageSrc}
          initialCorners={initialCorners}
          initialDeskewAngle={0}
          onConfirm={(cropData: { points: Point[]; horizontalTilt: number; verticalTilt: number }) => {
            onConfirmCrop(cropData);
          }}
        />
      </div>
    </div>
  );
}
