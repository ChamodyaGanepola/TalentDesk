"use client";

import { UploadCloud, Loader2 } from "lucide-react";
import { useState } from "react";
import UploadFilterModal from "@/app/components/UploadFilterModal";

type Props = {
  onUploadSuccess?: () => void;
};

export default function UploadSection({ onUploadSuccess }: Props) {
  const [successMessage, setSuccessMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [openModal, setOpenModal] = useState(false);

  const handleUpload = async (files: FileList) => {
    setUploading(true);

    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/upload/cvs`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();

      if (res.ok) {
        setSuccessMessage(`Uploaded successfully: ${data.count} files`);
        onUploadSuccess?.();
      } else {
        setSuccessMessage(data.error || "Upload failed");
      }
    } catch {
      setSuccessMessage("Server error");
    } finally {
      setUploading(false);
      setTimeout(() => setSuccessMessage(""), 3000);
    }
  };

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed border-cyan-300 text-center">

      {successMessage && (
        <div className="mb-5 bg-green-100 text-green-700 px-4 py-3 rounded-xl">
          {successMessage}
        </div>
      )}

      <div className="flex justify-center mb-5">
        <div className="w-20 h-20 rounded-full bg-cyan-100 flex items-center justify-center">
          <UploadCloud size={40} className="text-cyan-600" />
        </div>
      </div>

      <h2 className="text-2xl font-bold">Bulk Upload CVs</h2>

      <input
        type="file"
        multiple
        className="hidden"
        id="cvUpload"
        disabled={uploading}
        accept=".pdf,.doc,.docx,.xls,.xlsx"
        onChange={(e) => {
          if (!e.target.files) return;

          const files = Array.from(e.target.files);

          const allowed = files.filter((file) => {
            const ext = file.name.split(".").pop()?.toLowerCase();
            return (
              ext === "pdf" ||
              ext === "doc" ||
              ext === "docx" ||
              ext === "xlsx" ||
              ext === "xls"
            );
          });

          if (allowed.length !== files.length) {
            setSuccessMessage("Only CV (PDF/DOC) or Excel files are allowed");
            return;
          }

          const dt = new DataTransfer();
          allowed.forEach((f) => dt.items.add(f));

          setSelectedFiles(dt.files);
          setOpenModal(true);
        }}
      />

      <label
        htmlFor="cvUpload"
        className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl font-semibold bg-cyan-600 text-white cursor-pointer"
      >
        {uploading ? (
          <>
            <Loader2 className="animate-spin" size={20} />
            Uploading...
          </>
        ) : (
          "Upload CV Files"
        )}
      </label>

      {openModal && selectedFiles && (
        <UploadFilterModal
          files={selectedFiles}
          onClose={() => setOpenModal(false)}
          onSuccess={() => {
            setOpenModal(false);
            onUploadSuccess?.();
          }}
        />
      )}
    </div>
  );
}