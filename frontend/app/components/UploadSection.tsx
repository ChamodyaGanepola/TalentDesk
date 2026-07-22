"use client";

import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { flushSync } from "react-dom";
import FilterModalLoadingShell from "@/app/components/FilterModalLoadingShell";
import UploadFilterModal from "@/app/components/UploadFilterModal";
import { prefetchMasters } from "@/app/lib/mastersCache";
import { useToast } from "@/app/components/ui/Toast";

function preloadFilterModal() {
  prefetchMasters();
  void import("@/app/components/UploadFilterModal");
}

type UploadProcessStatus =
  | null
  | "idle"
  | "processing"
  | "completed"
  | "no_results"
  | "failed";

type CompletionSummary = {
  total: number;
  shortlisted: number;
  rejected: number;
  failed: number;
} | null;

type Props = {
  status?: UploadProcessStatus;
  summary?: CompletionSummary;
  batchId?: string | null;
  uploadedCount?: number;
  onDismiss?: () => void;
  onUploadPending?: (fileCount: number) => void;
  onUploadFailed?: () => void;
  onUploadStarted?: (batchId: string, uploadedFiles: string[]) => void;
};

function SummaryPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "slate" | "green" | "red" | "amber" | "cyan";
}) {
  const tones = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-green-50 text-green-700",
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-700",
    cyan: "bg-cyan-50 text-cyan-700",
  };

  return (
    <div className={`rounded-xl px-3 py-2 text-center ${tones[tone]}`}>
      <p className="text-lg font-bold leading-none">{value}</p>
      <p className="text-[11px] font-medium mt-1 opacity-80">{label}</p>
    </div>
  );
}

function StepItem({
  label,
  state,
}: {
  label: string;
  state: "done" | "active" | "pending";
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 flex-1 min-w-0">
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
          state === "done"
            ? "bg-cyan-600 border-cyan-600 text-white"
            : state === "active"
            ? "border-cyan-600 text-cyan-600 bg-white"
            : "border-slate-200 text-slate-400 bg-white"
        }`}
      >
        {state === "done" ? "✓" : state === "active" ? "•" : ""}
      </div>
      <span
        className={`text-[11px] font-medium text-center leading-tight ${
          state === "active" ? "text-cyan-700" : "text-slate-500"
        }`}
      >
        {label}
      </span>
    </div>
  );
}

function UploadStatusCard({
  status,
  summary,
  batchId,
  uploadedCount,
  onDismiss,
}: {
  status: Exclude<UploadProcessStatus, null | "idle">;
  summary: CompletionSummary;
  batchId?: string | null;
  uploadedCount?: number;
  onDismiss?: () => void;
}) {
  const isProcessing = status === "processing";
  const isCompleted = status === "completed";
  const isNoResults = status === "no_results";

  const cardStyles = isProcessing
    ? "border-cyan-200 bg-gradient-to-br from-cyan-50 to-white"
    : isCompleted
    ? "border-green-200 bg-gradient-to-br from-green-50 to-white"
    : isNoResults
    ? "border-amber-200 bg-gradient-to-br from-amber-50 to-white"
    : "border-red-200 bg-gradient-to-br from-red-50 to-white";

  const Icon = isProcessing
    ? Loader2
    : isCompleted
    ? CheckCircle2
    : isNoResults
    ? AlertCircle
    : XCircle;

  const iconColor = isProcessing
    ? "text-cyan-600"
    : isCompleted
    ? "text-green-600"
    : isNoResults
    ? "text-amber-600"
    : "text-red-600";

  const title = isProcessing
    ? "Screening in progress"
    : isCompleted
    ? "Screening complete"
    : isNoResults
    ? "Screening finished — no matches"
    : "Screening failed";

  const subtitle = isProcessing
    ? uploadedCount
      ? `Analyzing ${uploadedCount} CV${uploadedCount === 1 ? "" : "s"} with your filters. This usually takes a moment.`
      : "Your CVs are being uploaded and analyzed. Please keep this page open."
    : isCompleted
    ? summary && summary.shortlisted > 0
      ? "Your shortlisted candidates are ready. Excel export has been generated."
      : "Processing finished, but no Excel file was generated."
    : isNoResults
    ? "All CVs were processed, but none matched your screening criteria."
    : "Something went wrong while processing. Check recent uploads for details.";

  return (
    <div className={`mt-6 rounded-2xl border p-5 text-left shadow-sm ${cardStyles}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div
            className={`shrink-0 w-11 h-11 rounded-xl bg-white/80 flex items-center justify-center shadow-sm ${iconColor}`}
          >
            <Icon
              size={24}
              className={isProcessing ? "animate-spin" : undefined}
            />
          </div>

          <div className="min-w-0">
            <h3 className="font-semibold text-slate-900">{title}</h3>
            <p className="text-sm text-slate-600 mt-0.5 leading-relaxed">
              {subtitle}
            </p>
          </div>
        </div>

        {!isProcessing && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white/70 transition"
            aria-label="Dismiss"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {isProcessing && (
        <div className="mt-5 space-y-4">
          <div className="flex items-center gap-2">
            <StepItem label="Upload" state="done" />
            <div className="h-0.5 flex-1 bg-cyan-200 rounded" />
            <StepItem label="AI screening" state="active" />
            <div className="h-0.5 flex-1 bg-slate-200 rounded" />
            <StepItem label="Results" state="pending" />
          </div>

          <div className="h-1.5 w-full bg-cyan-100 rounded-full overflow-hidden relative">
            <div className="absolute inset-y-0 left-0 w-2/5 bg-cyan-500 rounded-full animate-pulse" />
          </div>
        </div>
      )}

      {!isProcessing && summary && (
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
          <SummaryPill label="Total" value={summary.total} tone="slate" />
          <SummaryPill
            label="Shortlisted"
            value={summary.shortlisted}
            tone="green"
          />
          <SummaryPill label="Rejected" value={summary.rejected} tone="red" />
          {summary.failed > 0 && (
            <SummaryPill label="Failed" value={summary.failed} tone="amber" />
          )}
        </div>
      )}

      {!isProcessing && batchId && (
        <div className="mt-4 flex flex-wrap gap-2">
          {isCompleted && summary && summary.shortlisted > 0 && (
            <Link
              href={`/resume-viewer?batch=${batchId}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white text-sm font-medium transition"
            >
              <FileSpreadsheet size={16} />
              Open Excel
            </Link>
          )}

          <Link
            href={`/batch-details?batch=${batchId}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-sm font-medium transition"
          >
            View batch details
          </Link>
        </div>
      )}
    </div>
  );
}

export default function UploadSection({
  status = null,
  summary = null,
  batchId = null,
  uploadedCount = 0,
  onDismiss,
  onUploadPending,
  onUploadFailed,
  onUploadStarted,
}: Props) {
  const { showToast } = useToast();
  const [openModal, setOpenModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  useEffect(() => {
    preloadFilterModal();
  }, []);

  const closeModal = () => {
    setOpenModal(false);
    setSelectedFiles(null);
  };

  const handleFileChange = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    // Show filter card shell on the very next paint — before file validation.
    flushSync(() => {
      setOpenModal(true);
      setSelectedFiles(null);
    });

    const validFiles = Array.from(fileList).filter((file) =>
      file.name.toLowerCase().endsWith(".pdf")
    );

    if (validFiles.length === 0) {
      setOpenModal(false);
      setSelectedFiles(null);
      showToast("Only PDF files are allowed.", "error");
      return;
    }

    const dataTransfer = new DataTransfer();
    validFiles.forEach((file) => dataTransfer.items.add(file));

    preloadFilterModal();
    setSelectedFiles(dataTransfer.files);
  };

  const isProcessing = status === "processing";
  const showStatusCard =
    status === "processing" ||
    status === "completed" ||
    status === "no_results" ||
    status === "failed";

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed border-slate-300 text-center">
      <div className="flex justify-center mb-5">
        <div className="w-20 h-20 rounded-full bg-cyan-100 flex items-center justify-center">
          {isProcessing ? (
            <Loader2 size={40} className="text-cyan-600 animate-spin" />
          ) : (
            <UploadCloud size={40} className="text-cyan-600" />
          )}
        </div>
      </div>

      <h2 className="text-2xl font-bold text-slate-900">Bulk Upload CVs</h2>

      <p className="text-sm text-slate-500 mt-2">
        {isProcessing
          ? "Your batch is being processed in the background."
          : "Upload PDF CV files and apply screening filters."}
      </p>

      <input
        type="file"
        multiple
        id="cvUpload"
        className="hidden"
        accept=".pdf,application/pdf"
        disabled={isProcessing}
        onMouseDown={preloadFilterModal}
        onChange={(e) => {
          if (isProcessing) return;
          handleFileChange(e.target.files);
          e.target.value = "";
        }}
      />

      <label
        htmlFor={isProcessing ? undefined : "cvUpload"}
        aria-disabled={isProcessing}
        onMouseEnter={preloadFilterModal}
        onFocus={preloadFilterModal}
        className={`px-8 py-4 rounded-2xl inline-flex mt-5 transition text-white ${
          isProcessing
            ? "bg-slate-300 cursor-not-allowed pointer-events-none"
            : "bg-cyan-600 hover:bg-cyan-700 cursor-pointer"
        }`}
      >
        {isProcessing ? "Processing CVs..." : "Upload CV Files"}
      </label>

      {openModal && !selectedFiles && (
        <FilterModalLoadingShell onClose={closeModal} />
      )}

      {openModal && selectedFiles && (
        <UploadFilterModal
          files={selectedFiles}
          onClose={closeModal}
          onUploadPending={() => {
            const count = selectedFiles?.length ?? 0;
            setOpenModal(false);
            onUploadPending?.(count);
          }}
          onUploadFailed={() => {
            setOpenModal(true);
            onUploadFailed?.();
          }}
          onProcessingStart={(id, uploadedFiles) => {
            setSelectedFiles(null);
            onUploadStarted?.(id, uploadedFiles);
          }}
        />
      )}

      {showStatusCard && (
        <UploadStatusCard
          status={status}
          summary={summary}
          batchId={batchId}
          uploadedCount={uploadedCount}
          onDismiss={onDismiss}
        />
      )}
    </div>
  );
}
