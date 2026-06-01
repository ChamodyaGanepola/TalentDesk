"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";

import { FileText, Eye, Download, Search, Filter } from "lucide-react";

type ExcelFile = {
  id: number;
  batch_id: string;
  file: string;
  created_at?: string;
};

export default function ResumeViewerPage() {
  const [search, setSearch] = useState("");
  const [files, setFiles] = useState<ExcelFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
  const fetchFiles = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/batch/excels`
      );

      const data = await res.json();

      setFiles(Array.isArray(data) ? data : []);
    } catch (err) {
      console.log(err);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  fetchFiles();
}, []);



  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />

        {/* Search */}
        <div className="bg-white rounded-2xl shadow-sm p-4 mb-8 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 bg-slate-100 px-4 py-3 rounded-xl w-full max-w-md">
            <Search size={18} className="text-slate-400" />
            <input
              type="text"
              placeholder="Search resumes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none w-full text-sm"
            />
          </div>

          <button className="flex items-center gap-2 bg-cyan-600 text-white px-5 py-3 rounded-xl">
            <Filter size={18} />
            Filter
          </button>
        </div>

        {/* List */}
        <div className="space-y-5">
          {loading ? (
            <p className="text-slate-500">Loading resumes...</p>
          ) : (
         files.map((file) => (
  <div
    key={file.id}
    className="bg-white rounded-3xl shadow-sm p-6 flex items-center justify-between"
  >
    <div>
      <h2 className="font-semibold text-lg">
         Batch: {file.batch_id}
      </h2>

      <p className="text-sm text-gray-500">
        Excel Generated: {file.file}
      </p>

      <p className="text-xs text-gray-400">
        {file.created_at}
      </p>
    </div>

   <a
  href={`${process.env.NEXT_PUBLIC_API_URL}/${file.file}`}
  target="_blank"
  rel="noreferrer"
>
      Download Excel
    </a>
  </div>
))
          )}
        </div>
      </main>
    </div>
  );
}