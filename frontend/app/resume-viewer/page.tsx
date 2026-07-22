"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";
import { ExcelListSkeleton } from "@/app/components/Skeletons";
import { formatSLDateTime } from "@/app/lib/datetime";
import AuthGuard from "@/app/components/AuthGuard";
import { useToast } from "@/app/components/ui/Toast";
import { getAuthHeaders } from "@/app/lib/auth";
import { Download, Filter, Loader2 } from "lucide-react";
import { useSearchParams } from "next/navigation";

type ExcelFile = {
  id: number;
  batch_id: string;
  file: string;
  created_at?: string | null;
};

const API = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const PER_PAGE = 10;

function getExcelUrl(filePath: string) {
  const clean = filePath.replace(/\\/g, "/").replace(/^\/+/, "");
  if (clean.startsWith("http://") || clean.startsWith("https://")) return clean;
  if (clean.startsWith("exports/")) return `${API}/${clean}`;
  return `${API}/exports/${clean.split("/").pop()}`;
}

function ResumeViewerContent() {
  const searchParams = useSearchParams();
  const batchFromUrl = searchParams.get("batch");
  const { showToast } = useToast();

  const [filterDate, setFilterDate] = useState("");
  const [files, setFiles] = useState<ExcelFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const fetchFiles = useCallback(
    async (
      cursor: string | null = null,
      opts?: { date?: string }
    ) => {
      const activeDate = opts?.date !== undefined ? opts.date : filterDate;
      setLoading(true);

      try {
        if (batchFromUrl) {
          const exportRes = await fetch(
            `${API}/resume/export/${batchFromUrl}`,
            { headers: getAuthHeaders() }
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
            setNextCursor(null);
            setHasMore(false);
            setCursorStack([null]);
          } else {
            setFiles([]);
            setNextCursor(null);
            setHasMore(false);
            setCursorStack([null]);
          }
          return;
        }

        const params = new URLSearchParams();
        params.set("per_page", String(PER_PAGE));
        if (cursor) params.set("cursor", cursor);
        if (activeDate) params.set("date", activeDate);

        const res = await fetch(`${API}/batch/excels?${params.toString()}`, {
          headers: getAuthHeaders(),
        });
        const data = await res.json();

        setFiles(data.data || []);
        setNextCursor(data.next_cursor || null);
        setHasMore(Boolean(data.has_more));
      } catch (err) {
        console.error("Excel fetch failed:", err);
        setFiles([]);
        setNextCursor(null);
        setHasMore(false);
      } finally {
        setLoading(false);
      }
    },
    [batchFromUrl, filterDate]
  );

  useEffect(() => {
    setCursorStack([null]);
    fetchFiles(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchFromUrl]);

  const applyFilter = () => {
    setCursorStack([null]);
    fetchFiles(null);
    showToast("Date filter applied.", "success");
  };

  const goToNextPage = () => {
    if (!nextCursor) return;
    setCursorStack((prev) => [...prev, nextCursor]);
    fetchFiles(nextCursor);
  };

  const goToPrevPage = () => {
    setCursorStack((prev) => {
      if (prev.length <= 1) return prev;
      const newStack = prev.slice(0, -1);
      const prevCursor = newStack[newStack.length - 1] ?? null;
      fetchFiles(prevCursor);
      return newStack;
    });
  };

  const downloadExcel = async (file: ExcelFile) => {
    setDownloadingId(file.id);
    try {
      const res = await fetch(getExcelUrl(file.file), { headers: getAuthHeaders() });

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
      showToast("Excel downloaded successfully.", "success");
    } catch (err) {
      console.error("Download failed:", err);
      showToast("Download failed. Please try again.", "error");
    } finally {
      setDownloadingId(null);
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

          {!batchFromUrl && (
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
                onClick={applyFilter}
              >
                <Filter size={18} />
                Filter
              </button>

              {filterDate && (
                <button
                  type="button"
                  className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900"
                  onClick={() => {
                    setFilterDate("");
                    setCursorStack([null]);
                    fetchFiles(null, { date: "" });
                    showToast("Date filter cleared.", "info");
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          )}
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
                  disabled={downloadingId === file.id}
                  className="inline-flex items-center gap-2 text-cyan-600 font-medium hover:text-cyan-800 disabled:opacity-50"
                  onClick={() => downloadExcel(file)}
                >
                  {downloadingId === file.id ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Download size={18} />
                  )}
                  {downloadingId === file.id ? "Downloading..." : "Download Excel"}
                </button>
              </div>
            ))
          )}
        </div>

        {!batchFromUrl && (cursorStack.length > 1 || hasMore) && (
          <div className="flex items-center justify-center gap-3 mt-6 text-slate-900">
            <button
              disabled={cursorStack.length <= 1 || loading}
              onClick={goToPrevPage}
              className="px-3 py-2 bg-white rounded disabled:opacity-40"
            >
              Prev
            </button>

            <span className="text-sm text-slate-500">Page {cursorStack.length}</span>

            <button
              disabled={!hasMore || loading}
              onClick={goToNextPage}
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
    <AuthGuard>
      <Suspense
        fallback={
          <div className="min-h-screen bg-slate-100 p-8">
            <ExcelListSkeleton />
          </div>
        }
      >
        <ResumeViewerContent />
      </Suspense>
    </AuthGuard>
  );
}
