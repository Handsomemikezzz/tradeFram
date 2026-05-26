import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, X, ZoomIn, ZoomOut } from 'lucide-react';
import { resolveImageUrl } from './MultiImageUpload';

interface ImageLightboxProps {
  images: string[];
  startIndex: number;
  onClose: () => void;
}

export function ImageLightbox({ images, startIndex, onClose }: ImageLightboxProps) {
  const [index, setIndex] = useState(startIndex);
  const [zoom, setZoom] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') handlePrev();
      if (e.key === 'ArrowRight') handleNext();
    };

    window.addEventListener('keydown', handleKeyDown);
    // Lock body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [index]);

  const handlePrev = () => {
    setZoom(false);
    setIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1));
  };

  const handleNext = () => {
    setZoom(false);
    setIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1));
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-between bg-slate-950/95 p-4 backdrop-blur-sm">
      {/* Top Bar */}
      <div className="flex w-full items-center justify-between text-white md:px-8">
        <span className="font-mono text-sm font-medium text-slate-400">
          图表 {index + 1} / {images.length}
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setZoom((z) => !z)}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/50 hover:bg-slate-800 text-slate-200 transition"
          >
            {zoom ? <ZoomOut className="h-5 w-5" /> : <ZoomIn className="h-5 w-5" />}
          </button>
          <button
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800/50 hover:bg-slate-800 text-slate-200 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Main Image Container */}
      <div className="relative flex flex-1 w-full items-center justify-center">
        {images.length > 1 && (
          <button
            onClick={handlePrev}
            className="absolute left-4 z-10 flex h-12 w-12 items-center justify-center rounded-full bg-slate-900/60 text-white hover:bg-slate-900/90 hover:scale-105 transition active:scale-95"
          >
            <ChevronLeft className="h-6 w-6" />
          </button>
        )}

        <div className="flex items-center justify-center max-h-[80vh] max-w-[85vw] overflow-auto select-none rounded-lg bg-slate-900/30 p-2 border border-slate-800/30">
          <img
            src={resolveImageUrl(images[index])}
            alt={`Fullscreen review chart ${index + 1}`}
            className={`transition-all duration-300 max-h-[75vh] max-w-[80vw] object-contain rounded-md shadow-2xl ${
              zoom ? 'scale-125 cursor-zoom-out' : 'cursor-zoom-in'
            }`}
            onClick={() => setZoom((z) => !z)}
          />
        </div>

        {images.length > 1 && (
          <button
            onClick={handleNext}
            className="absolute right-4 z-10 flex h-12 w-12 items-center justify-center rounded-full bg-slate-900/60 text-white hover:bg-slate-900/90 hover:scale-105 transition active:scale-95"
          >
            <ChevronRight className="h-6 w-6" />
          </button>
        )}
      </div>

      {/* Footer Navigation Hints */}
      <div className="pb-4 text-center text-xs text-slate-500 font-medium">
        提示：支持按键盘左右方向键 ← / → 翻页，Esc 键退出
      </div>
    </div>
  );
}
