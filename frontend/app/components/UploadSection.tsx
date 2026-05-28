"use client";

import { UploadCloud } from "lucide-react";
import { useState } from "react";

type Props = {
  onUploadSuccess?: () => void;
};

export default function UploadSection({ onUploadSuccess }: Props) {
  const [successMessage, setSuccessMessage] = useState("");

  const handleUpload = async (files: FileList) => {
    const formData = new FormData();

    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/upload/cvs`,
      {
        method: "POST",
        body: formData,
      }
    );

    const data = await res.json();

    if (res.ok) {
      // ✅ success message instead of alert
      setSuccessMessage(`Uploaded successfully: ${data.count} files`);

      // auto hide after 3 sec
      setTimeout(() => {
        setSuccessMessage("");
      }, 3000);

      // refresh dashboard
      onUploadSuccess?.();
    } else {
      setSuccessMessage(data.error || "Upload failed");

      setTimeout(() => {
        setSuccessMessage("");
      }, 3000);
    }
  };

  return (
    <div className="bg-white rounded-3xl p-10 shadow-sm border border-dashed border-cyan-300 text-center">
      
      {/* SUCCESS MESSAGE */}
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

      <h2 className="text-2xl font-bold text-slate-800">
        Bulk Upload CVs
      </h2>

      <p className="text-slate-500 mt-3 mb-6">
        Upload multiple resumes for screening and analysis
      </p>

      <input
        type="file"
        multiple
        className="hidden"
        id="cvUpload"
        onChange={(e) => {
          if (e.target.files) {
            handleUpload(e.target.files);
          }
        }}
      />

      <label
        htmlFor="cvUpload"
        className="inline-block bg-cyan-600 hover:bg-cyan-700 text-white px-8 py-4 rounded-2xl cursor-pointer font-semibold transition"
      >
        Upload CV Files
      </label>
    </div>
  );
}