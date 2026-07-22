"use client";

import { Suspense, useEffect, useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";
import { ExcelListSkeleton } from "@/app/components/Skeletons";
import { formatSLDateTime } from "@/app/lib/datetime";
import { Download, Filter } from "lucide-react";
import { useSearchParams } from "next/navigation";

type ExcelFile = {
  id: number;
  batch_id: string;
  file: string;
  created_at?: string | null;
};

const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

const headers = {
  "ngrok-skip-browser-warning": "true",
};

function getExcelUrl(filePath: string) {
  const clean = filePath.replace(/\\/g, "/").replace(/^\/+/, "");
  if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;
  if (clean.startsWith("exports/")) return `${API}/${clean}`;
  return `${API}/exports/${clean.split("/").pop()}`;
}

function ResumeViewerContent() {
  const searchParams = useSearchParams();
  const batchFromUrl = searchParams.get("batch");

  const [filterDate, setFilterDate] = useState("");
  const [files, setFiles] = useState<ExcelFile[]>([]);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  const [perPage] = useState(5);
  const [total, setTotal] = useState(0);

  const totalPages = Math.ceil(total / perPage) || 1;

  const fetchFiles = async (pageNumber: number = 1) => {
    setLoading(true);

    try {
      // When a batch is selected, fetch that export directly so it always shows
      // (do not filter a paginated global list — newer UTC timestamps sorted after
      // older local timestamps and the file looked "missing").
      if (batchFromUrl) {
        const exportRes = await fetch(
          `${API}/resume/export/${batchFromUrl}`,
          { headers }
        );
        const exportData = await exportRes.json();

        if (exportData?.excel_file) {
          setFiles([
            {
              id: 0,
              batch_id: batchFromUrl,
              file: String(exportData.excel_file).replace(/\\/g, "/"),
              created_at: exportData.created_at || null,
            },
          ]);
          setTotal(1);
          setPage(1);
        } else {
          setFiles([]);
          setTotal(0);
          setPage(1);
        }
        return;
      }

      let url = `${API}/batch/excels?page=${pageNumber}&per_page=${perPage}`;

      if (filterDate) {
        url += `&date=${filterDate}`;
      }

      const res = await fetch(url, { headers });
      const data = await res.json();

      setFiles(data.data || []);
      setTotal(data.total || 0);
      setPage(data.page || pageNumber);
    } catch (err) {
      console.error("Excel fetch failed:", err);
      setFiles([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchFromUrl]);

  const downloadExcel = async (file: ExcelFile) => {
    try {
      const res = await fetch(getExcelUrl(file.file), { headers });

      if (!res.ok) {
        throw new Error("Download failed");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download =
        file.file.replace(/\\/g, "/").split("/").pop() || "resume.xlsx";

      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
      alert("Download failed. Please try again.");
    }
  };

  const noData = !loading && files.length === 0;

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6 text-slate-900">
          <div>
            <h1 className="text-xl font-semibold">Exported Excel Files</h1>

            {batchFromUrl && (
              <p className="text-sm text-slate-500 mt-1">
                Showing batch: {batchFromUrl}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="bg-white border border-slate-200 px-4 py-2 rounded-xl outline-none text-sm"
            />

            <button
              type="button"
              className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-2 rounded-xl"
              onClick={() => fetchFiles(1)}
            >
              <Filter size={18} />
              Filter
            </button>
          </div>
        </div>

        <div className="space-y-5 text-slate-900">
          {loading ? (
            <ExcelListSkeleton />
          ) : noData ? (
            <div className="bg-white rounded-3xl shadow-sm text-center py-10 text-slate-500">
              No Excel files found.
            </div>
          ) : (
            files.map((file) => (
              <div
                key={file.id}
                className="bg-white rounded-3xl shadow-sm p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
              >
                <div>
                  <h2 className="font-semibold text-lg text-slate-900">
                    {file.file.replace(/\\/g, "/").split("/").pop() ||
                      "Excel export"}
                  </h2>

                  <p className="text-sm text-slate-500">
                    Generated: {formatSLDateTime(file.created_at)}
                  </p>

                  <p className="text-xs text-slate-400">
                    Batch: {file.batch_id}
                  </p>
                </div>

                <button
                  type="button"
                  className="inline-flex items-center gap-2 text-cyan-600 font-medium hover:text-cyan-800"
                  onClick={() => downloadExcel(file)}
                >
                  <Download size={18} />
                  Download Excel
                </button>
              </div>
            ))
          )}
        </div>

        {!batchFromUrl && totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6 text-slate-900">
            <button
              disabled={page === 1 || loading}
              onClick={() => fetchFiles(page - 1)}
              className="px-3 py-2 bg-white rounded disabled:opacity-40"
            >
              Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => fetchFiles(p)}
                className={`px-3 py-2 rounded ${
                  p === page ? "bg-cyan-600 text-white" : "bg-white"
                }`}
              >
                {p}
              </button>
            ))}

            <button
              disabled={page === totalPages || loading}
              onClick={() => fetchFiles(page + 1)}
              className="px-3 py-2 bg-white rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ResumeViewerPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-100 p-8">
          <ExcelListSkeleton />
        </div>
      }
    >
      <ResumeViewerContent />
    </Suspense>
  );
}
