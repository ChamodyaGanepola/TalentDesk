"use client";

import { UploadCloud } from "lucide-react";
import { useState } from "react";
import UploadFilterModal from "@/app/components/UploadFilterModal";

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
  onUploadStarted?: (batchId: string) => void;
};

export default function UploadSection({
  status = null,
  summary = null,
  onUploadStarted,
}: Props) {
  const [openModal, setOpenModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const handleFileChange = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    const validFiles = Array.from(fileList).filter((file) =>
      file.name.toLowerCase().endsWith(".pdf")
    );

    if (validFiles.length === 0) {
      alert("Only PDF files are allowed.");
      return;
    }

    const dataTransfer = new DataTransfer();

    validFiles.forEach((file) => {
      dataTransfer.items.add(file);
    });

    setSelectedFiles(dataTransfer.files);
    setOpenModal(true);
  };

  const summaryText = summary
    ? `${summary.shortlisted} shortlisted, ${summary.rejected} rejected` +
      (summary.failed ? `, ${summary.failed} failed` : "") +
      ` (of ${summary.total} CVs)`
    : null;

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed border-slate-300 text-center">
      <div className="flex justify-center mb-5">
        <div className="w-20 h-20 rounded-full bg-cyan-100 flex items-center justify-center">
          <UploadCloud size={40} className="text-cyan-600" />
        </div>
      </div>

      <h2 className="text-2xl font-bold text-slate-900">Bulk Upload CVs</h2>

      <p className="text-sm text-slate-500 mt-2">
        Upload PDF CV files and apply screening filters.
      </p>

      <input
        type="file"
        multiple
        id="cvUpload"
        className="hidden"
        accept=".pdf,application/pdf"
        onChange={(e) => {
          handleFileChange(e.target.files);
          e.target.value = "";
        }}
      />

      <label
        htmlFor="cvUpload"
        className="px-8 py-4 bg-cyan-600 hover:bg-cyan-700 text-white rounded-2xl cursor-pointer inline-flex mt-5 transition"
      >
        Upload CV Files
      </label>

      {openModal && selectedFiles && (
        <UploadFilterModal
          files={selectedFiles}
          onClose={() => {
            setOpenModal(false);
            setSelectedFiles(null);
          }}
          onProcessingStart={(batchId: string) => {
            setOpenModal(false);
            setSelectedFiles(null);
            onUploadStarted?.(batchId);
          }}
        />
      )}

      {status === "processing" && (
        <p className="mt-5 text-cyan-600 font-medium animate-pulse">
          Processing CVs...
        </p>
      )}

      {status === "completed" && (
        <p className="mt-5 text-green-600 font-medium">
          Processing completed
          {summaryText ? `: ${summaryText}.` : "."} Redirecting to Resume
          Viewer...
        </p>
      )}

      {status === "no_results" && (
        <p className="mt-5 text-red-600 font-medium">
          Processing completed
          {summaryText ? `: ${summaryText}.` : "."} No candidates were
          shortlisted, so no Excel file was generated.
        </p>
      )}

      {status === "failed" && (
        <p className="mt-5 text-red-600 font-medium">
          Processing failed
          {summaryText ? `: ${summaryText}.` : "."} Please check recent uploads.
        </p>
      )}
    </div>
  );
}
