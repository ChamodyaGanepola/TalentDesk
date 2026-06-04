"use client";

import { UploadCloud } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import UploadFilterModal from "@/app/components/UploadFilterModal";
import { useRouter } from "next/navigation";

export default function UploadSection({ onUploadSuccess }: any) {

  const [openModal, setOpenModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const WS_URL = process.env.NEXT_PUBLIC_WS_URL;
  const [status, setStatus] = useState<
    null | "processing" | "rejected" | "completed"
  >(null);

  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);

  const onUploadSuccessRef = useRef(onUploadSuccess);

  useEffect(() => {
    onUploadSuccessRef.current = onUploadSuccess;
  }, [onUploadSuccess]);

  const resetStatusAfterDelay = () => {
    setTimeout(() => setStatus(null), 3000);
  };

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/ws/dashboard`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // 🔥 REAL-TIME CV UPDATE (NEW)
      if (data.event === "cv_processed") {
        setStatus("processing");
        return;
      }

      // batch no results
      if (data.event === "batch_completed_no_results") {
        setStatus("rejected");
        onUploadSuccessRef.current?.();
        resetStatusAfterDelay();
      }

      // batch completed
      if (data.event === "batch_completed") {
        setStatus("completed");
        onUploadSuccessRef.current?.();
        resetStatusAfterDelay();
      }

      // excel ready → navigate
      if (data.event === "excel_exported") {
        setStatus("completed");

        setTimeout(() => {
          router.push(`/resume-viewer?batch=${data.batch_id}`);
        }, 800);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed text-center">

      <div className="flex justify-center mb-5">
        <div className="w-20 h-20 rounded-full bg-cyan-100 flex items-center justify-center">
          <UploadCloud size={40} className="text-cyan-600" />
        </div>
      </div>

      <h2 className="text-2xl font-bold">Bulk Upload CVs</h2>

      <input
        type="file"
        multiple
        id="cvUpload"
        className="hidden"
        accept=".pdf,.doc,.docx"
        onChange={(e) => {
          if (!e.target.files) return;

          const filesArray = Array.from(e.target.files);

          const dt = new DataTransfer();
          filesArray.forEach((f) => dt.items.add(f));

          setSelectedFiles(dt.files);
          setOpenModal(true);

          e.target.value = "";
        }}
      />

      <label
        htmlFor="cvUpload"
        className="px-8 py-4 bg-cyan-600 text-white rounded-2xl cursor-pointer inline-flex mt-5"
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
          onProcessingStart={() => {
            setOpenModal(false);
            setStatus("processing");
          }}
        />
      )}

      {status === "processing" && (
        <p className="mt-5 text-cyan-600 font-medium animate-pulse">
          Processing CVs...
        </p>
      )}

      {status === "rejected" && (
        <p className="mt-5 text-red-600 font-medium">
          All CVs were rejected
        </p>
      )}

      {status === "completed" && (
        <p className="mt-5 text-green-600 font-medium">
          Processing completed
        </p>
      )}
    </div>
  );
}