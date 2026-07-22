"use client";

import { AlertTriangle, Loader2 } from "lucide-react";

type Props = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "primary",
  loading = false,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null;

  const confirmClass =
    variant === "danger"
      ? "bg-red-600 hover:bg-red-700 text-white"
      : "bg-cyan-600 hover:bg-cyan-700 text-white";

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
        onClick={loading ? undefined : onCancel}
        aria-hidden
      />

      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
        className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
      >
        <div className="flex items-start gap-3">
          <div
            className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${
              variant === "danger"
                ? "bg-red-100 text-red-600"
                : "bg-cyan-100 text-cyan-600"
            }`}
          >
            <AlertTriangle size={20} />
          </div>

          <div className="min-w-0">
            <h3 id="confirm-title" className="font-semibold text-slate-900">
              {title}
            </h3>
            <p id="confirm-message" className="text-sm text-slate-600 mt-1">
              {message}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
          >
            {cancelLabel}
          </button>

          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50 ${confirmClass}`}
          >
            {loading && <Loader2 size={16} className="animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
