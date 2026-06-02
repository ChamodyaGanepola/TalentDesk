"use client";

import { UploadCloud } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import UploadFilterModal from "@/app/components/UploadFilterModal";
import { useRouter } from "next/navigation";

export default function UploadSection({ onUploadSuccess }: any) {
  const [openModal, setOpenModal] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  const [status, setStatus] = useState<
    null | "processing" | "rejected" | "completed"
  >(null);

  const router = useRouter();
  const wsRef = useRef<WebSocket | null>(null);

  // =============================
  // WEBSOCKET LISTENER
  // =============================
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/dashboard");
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // ❌ All rejected
      if (data.event === "batch_completed_no_results") {
        setStatus("rejected");
        onUploadSuccess?.();
        // auto-hide after 3s
        setTimeout(() => setStatus(null), 3000);
      }

      // ✅ Batch done (some shortlisted exist)
      if (data.event === "batch_completed") {
        setStatus("completed");
        onUploadSuccess?.();
        // auto-hide after 3s
        setTimeout(() => setStatus(null), 3000);
      }

      // 📦 Excel generated → redirect
      if (data.event === "excel_exported") {
        setStatus("completed");
        setTimeout(() => {
          router.push("/resume-viewer");
        }, 800);
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed text-center">

      {/* ICON */}
      <div className="flex justify-center mb-5">
        <div className="w-20 h-20 rounded-full bg-cyan-100 flex items-center justify-center">
          <UploadCloud size={40} className="text-cyan-600" />
        </div>
      </div>

      <h2 className="text-2xl font-bold">Bulk Upload CVs</h2>

      {/* FILE INPUT */}
      <input
        type="file"
        multiple
        id="cvUpload"
        className="hidden"
        accept=".pdf,.doc,.docx"
        onChange={(e) => {
          if (!e.target.files) return;
          setSelectedFiles(e.target.files);
          setOpenModal(true);
        }}
      />

      <label
        htmlFor="cvUpload"
        className="px-8 py-4 bg-cyan-600 text-white rounded-2xl cursor-pointer inline-flex mt-5"
      >
        Upload CV Files
      </label>

      {/* MODAL */}
      {openModal && selectedFiles && (
        <UploadFilterModal
          files={selectedFiles}
          onClose={() => setOpenModal(false)}
          onProcessingStart={() => {
            setOpenModal(false);
            setStatus("processing");
          }}
        />
      )}

      {/* =============================
          STATUS DISPLAY (SMART UI)
          ============================= */}

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