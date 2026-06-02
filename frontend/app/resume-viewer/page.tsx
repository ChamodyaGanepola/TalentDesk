"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";

import { Filter } from "lucide-react";

type ExcelFile = {
  id: number;
  batch_id: string;
  file: string;
  created_at?: string;
};

export default function ResumeViewerPage() {
  const [filterDate, setFilterDate] = useState("");
  const [files, setFiles] = useState<ExcelFile[]>([]);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  const [perPage] = useState(2);
  const [total, setTotal] = useState(0);

  const totalPages = Math.ceil(total / perPage);

  const fetchFiles = async (pageNumber: number = 1) => {
    setLoading(true);

    try {
      let url = `${process.env.NEXT_PUBLIC_API_URL}/batch/excels?page=${pageNumber}&per_page=${perPage}`;

      if (filterDate) {
        url += `&date=${filterDate}`;
      }

      const res = await fetch(url);
      const data = await res.json();

      setFiles(data.data || []);
      setTotal(data.total || 0);
      setPage(data.page || 1);
    } catch (err) {
      console.log(err);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles(1);
  }, []);

  const noData = !loading && files.length === 0;

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />

        {/* FILTER */}
        <div className="flex items-center gap-3 mb-6">
          <input
            type="date"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="bg-slate-100 px-4 py-2 rounded-xl outline-none text-sm"
          />

          <button
            className="flex items-center gap-2 bg-cyan-600 text-white px-5 py-2 rounded-xl"
            onClick={() => fetchFiles(1)}
          >
            <Filter size={18} /> Filter
          </button>
        </div>

        {/* LIST */}
        <div className="space-y-5 text-black">
          {loading ? (
            <p className="text-slate-500">Loading resumes...</p>
          ) : noData ? (
            <div className="text-center py-10 text-slate-500">
              No Excel files found for selected filter.
            </div>
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

                <button
                  className="text-cyan-600 font-medium"
                  onClick={async () => {
                    try {
                      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/${file.file}`);
                      const blob = await res.blob();
                      const url = window.URL.createObjectURL(blob);

                      const a = document.createElement("a");
                      a.href = url;
                      a.download = file.file.split("/").pop() || "resume.xlsx";
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                      window.URL.revokeObjectURL(url);
                    } catch (err) {
                      console.error("Download failed", err);
                    }
                  }}
                >
                  Download Excel
                </button>
              </div>
            ))
          )}
        </div>

        {/* PAGINATION */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6 text-black">
            <button
              disabled={page === 1}
              onClick={() => fetchFiles(page - 1)}
              className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
            >
              Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => fetchFiles(p)}
                className={`px-3 py-2 rounded ${p === page ? "bg-cyan-600 text-white" : "bg-slate-100"
                  }`}
              >
                {p}
              </button>
            ))}

            <button
              disabled={page === totalPages}
              onClick={() => fetchFiles(page + 1)}
              className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}