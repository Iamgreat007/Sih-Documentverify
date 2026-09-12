"use client";
import React, { useState, useRef, useEffect, useCallback } from 'react';

const ManualCrop = ({ imageSrc, onConfirm, initialCorners, initialDeskewAngle }) => {
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const [points, setPoints] = useState([
    { x: 0, y: 0 },   // Top-Left
    { x: 100, y: 0 },  // Top-Right
    { x: 100, y: 100 }, // Bottom-Right
    { x: 0, y: 100 },  // Bottom-Left
  ]);
  const draggingIdxRef = useRef(null);
  const [draggingIdx, setDraggingIdx] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [horizontalTilt, setHorizontalTilt] = useState(initialDeskewAngle || 0);
  const [verticalTilt, setVerticalTilt] = useState(0);
  const [imgOffset, setImgOffset] = useState({ x: 0, y: 0 }); // offset of image within container

  // Initialize corner points: use detected corners if available, else full image bounds
  useEffect(() => {
    if (imageLoaded && imageRef.current && containerRef.current) {
      const img = imageRef.current;
      const imgRect = img.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      
      // Calculate image offset within container (could be non-zero if container is larger)
      const offsetX = imgRect.left - containerRect.left;
      const offsetY = imgRect.top - containerRect.top;
      setImgOffset({ x: offsetX, y: offsetY });

      const displayWidth = imgRect.width;
      const displayHeight = imgRect.height;

      if (initialCorners && initialCorners.length === 4) {
        // Map detected corners from original image coords to display coords
        const naturalW = img.naturalWidth;
        const naturalH = img.naturalHeight;
        const scaleX = displayWidth / naturalW;
        const scaleY = displayHeight / naturalH;

        setPoints(initialCorners.map(pt => ({
          x: pt.x * scaleX + offsetX,
          y: pt.y * scaleY + offsetY
        })));
      } else {
        // Default: slight inset from edges
        const margin = Math.min(displayWidth, displayHeight) * 0.05;
        setPoints([
          { x: offsetX + margin, y: offsetY + margin },
          { x: offsetX + displayWidth - margin, y: offsetY + margin },
          { x: offsetX + displayWidth - margin, y: offsetY + displayHeight - margin },
          { x: offsetX + margin, y: offsetY + displayHeight - margin },
        ]);
      }
    }
  }, [imageLoaded, initialCorners]);

  // Get position from mouse or touch event
  const getEventPos = useCallback((e) => {
    const rect = containerRef.current.getBoundingClientRect();
    if (e.touches && e.touches.length > 0) {
      return {
        x: e.touches[0].clientX - rect.left,
        y: e.touches[0].clientY - rect.top
      };
    }
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }, []);

  // Clamp point to image bounds
  const clampToImage = useCallback((pos) => {
    if (!imageRef.current || !containerRef.current) return pos;
    const imgRect = imageRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();
    const ox = imgRect.left - containerRect.left;
    const oy = imgRect.top - containerRect.top;
    return {
      x: Math.max(ox, Math.min(pos.x, ox + imgRect.width)),
      y: Math.max(oy, Math.min(pos.y, oy + imgRect.height))
    };
  }, []);

  // Handle drag start (mouse + touch)
  const handleDragStart = useCallback((idx, e) => {
    e.preventDefault();
    draggingIdxRef.current = idx;
    setDraggingIdx(idx);
  }, []);

  // Handle drag move (registered on document for reliable tracking)
  const handleDragMove = useCallback((e) => {
    if (draggingIdxRef.current === null) return;
    e.preventDefault();
    const pos = getEventPos(e);
    const clamped = clampToImage(pos);
    
    setPoints(prev => {
      const newPoints = [...prev];
      newPoints[draggingIdxRef.current] = clamped;
      return newPoints;
    });
  }, [getEventPos, clampToImage]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    draggingIdxRef.current = null;
    setDraggingIdx(null);
  }, []);

  // Register document-level mouse/touch events for reliable dragging
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

  const handleConfirm = () => {
    // Scale display coordinates back to original image coordinates
    const img = imageRef.current;
    if (img && containerRef.current) {
      const imgRect = img.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      const offsetX = imgRect.left - containerRect.left;
      const offsetY = imgRect.top - containerRect.top;

      const scaleX = img.naturalWidth / imgRect.width;
      const scaleY = img.naturalHeight / imgRect.height;

      const scaledPoints = points.map(pt => ({
        x: (pt.x - offsetX) * scaleX,
        y: (pt.y - offsetY) * scaleY
      }));

      onConfirm({
        points: scaledPoints,
        horizontalTilt,
        verticalTilt
      });
    } else {
      onConfirm({
        points,
        horizontalTilt,
        verticalTilt
      });
    }
  };

  // Corner label names
  const cornerLabels = ['TL', 'TR', 'BR', 'BL'];

  return (
    <div className="flex flex-col items-center bg-slate-900 p-4 rounded-3xl select-none">
      <div 
        ref={containerRef}
        className="relative cursor-crosshair rounded-lg border-2 border-slate-700"
        style={{ touchAction: 'none' }} 
      >
        <img 
          ref={imageRef}
          src={imageSrc} 
          className="max-w-full max-h-[70vh] h-auto select-none pointer-events-none" 
          alt="To Crop"
          draggable={false}
          onLoad={() => setImageLoaded(true)}
        />
        
        {/* SVG Overlay for the Crop Box */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 10 }}>
          {/* Dim area outside the crop polygon */}
          <defs>
            <mask id="cropMask">
              <rect width="100%" height="100%" fill="white" />
              <polygon 
                points={points.map(p => `${p.x},${p.y}`).join(' ')} 
                fill="black" 
              />
            </mask>
          </defs>
          <rect width="100%" height="100%" fill="rgba(0,0,0,0.5)" mask="url(#cropMask)" />
          
          {/* Crop border */}
          <polygon 
            points={points.map(p => `${p.x},${p.y}`).join(' ')} 
            fill="none" 
            stroke="#34d399" 
            strokeWidth="2.5" 
            strokeDasharray="8,4"
          />
          {/* Edge lines for clarity */}
          {points.map((p, i) => {
            const next = points[(i + 1) % 4];
            return (
              <line key={`edge-${i}`} x1={p.x} y1={p.y} x2={next.x} y2={next.y}
                stroke="#34d399" strokeWidth="2" />
            );
          })}
        </svg>

        {/* Draggable Corner Handles */}
        {points.map((p, i) => (
          <div
            key={i}
            onMouseDown={(e) => handleDragStart(i, e)}
            onTouchStart={(e) => handleDragStart(i, e)}
            style={{ 
              left: p.x - 16, 
              top: p.y - 16,
              zIndex: 30,
              touchAction: 'none'
            }}
            className={`absolute w-8 h-8 rounded-full cursor-move shadow-lg flex items-center justify-center
              ${draggingIdx === i ? 'bg-white border-3 border-emerald-400 scale-125' : 'bg-emerald-500 border-2 border-white'}
              transition-transform`}
          >
            <span className="text-[8px] font-bold text-slate-900 select-none">{cornerLabels[i]}</span>
          </div>
        ))}
      </div>

      {/* Rotation Controls */}
      <div className="w-full max-w-2xl mt-6 space-y-4">
        {/* Horizontal Tilt (Rotation) */}
        <div className="bg-slate-800 p-4 rounded-2xl">
          <div className="flex items-center justify-between mb-2">
            <label className="text-emerald-400 font-semibold flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              Horizontal Rotation
            </label>
            <span className="text-white font-mono bg-slate-700 px-3 py-1 rounded-lg">
              {horizontalTilt.toFixed(1)}°
            </span>
          </div>
          <input
            type="range"
            min="-45"
            max="45"
            step="0.5"
            value={horizontalTilt}
            onChange={(e) => setHorizontalTilt(parseFloat(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>-45°</span>
            <span>0°</span>
            <span>+45°</span>
          </div>
        </div>

        {/* Vertical Tilt (3D Perspective) */}
        <div className="bg-slate-800 p-4 rounded-2xl">
          <div className="flex items-center justify-between mb-2">
            <label className="text-emerald-400 font-semibold flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
              </svg>
              Vertical Perspective
            </label>
            <span className="text-white font-mono bg-slate-700 px-3 py-1 rounded-lg">
              {verticalTilt.toFixed(1)}°
            </span>
          </div>
          <input
            type="range"
            min="-45"
            max="45"
            step="0.5"
            value={verticalTilt}
            onChange={(e) => setVerticalTilt(parseFloat(e.target.value))}
            className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>-45°</span>
            <span>0°</span>
            <span>+45°</span>
          </div>
        </div>

        {/* Reset Button */}
        <button
          onClick={() => {
            setHorizontalTilt(0);
            setVerticalTilt(0);
          }}
          className="w-full bg-slate-700 text-white px-4 py-2 rounded-xl font-medium hover:bg-slate-600 transition"
        >
          Reset Rotation
        </button>
      </div>

      <button 
        onClick={handleConfirm}
        className="mt-6 bg-emerald-500 text-slate-950 px-8 py-3 rounded-2xl font-bold hover:bg-emerald-400 transition shadow-xl"
      >
        Apply Magic Filter
      </button>
    </div>
  );
};

export default ManualCrop;