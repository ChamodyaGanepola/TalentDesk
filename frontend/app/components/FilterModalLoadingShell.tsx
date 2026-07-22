"use client";

import { Loader2, Sparkles, X } from "lucide-react";
import { createPortal } from "react-dom";
import { FilterModalSkeleton } from "@/app/components/Skeletons";

export default function FilterModalLoadingShell({
  onClose,
}: {
  onClose?: () => void;
}) {
  const content = (
    <div className="fixed inset-0 z-[200] flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" aria-hidden />

      <div className="relative bg-white w-full sm:max-w-3xl max-h-[92vh] sm:max-h-[88vh] rounded-t-3xl sm:rounded-3xl shadow-2xl z-10 flex flex-col overflow-hidden">
        <div className="shrink-0 px-5 py-4 bg-gradient-to-r from-cyan-600 to-cyan-700 text-white">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Sparkles size={20} className="shrink-0 opacity-90" />
                <h2 className="text-lg font-bold">Screening filters</h2>
                <Loader2 size={16} className="animate-spin opacity-90" />
              </div>
              <p className="text-sm text-cyan-50 mt-1">Preparing your upload...</p>
            </div>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="shrink-0 p-2 rounded-xl bg-white/15 hover:bg-white/25 transition"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-5 bg-slate-50/80">
          <FilterModalSkeleton />
        </div>
      </div>
    </div>
  );

  if (typeof document === "undefined") return null;
  return createPortal(content, document.body);
}
