"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCard from "@/app/components/StatCards";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type UploadStatus =
  | "Uploaded"
  | "Processing"
  | "Shortlisted"
  | "Rejected"
  | "Failed";

type UploadItem = {
  id: number;
  batch_id: string;
  filename: string;
  file_url: string;
  stored_file: string;
  status: UploadStatus;
  created_at: string | null;
};

type Stats = {
  total: number;
  pending: number;
  processing: number;
  shortlisted: number;
  rejected: number;
  failed: number;
};

type UploadProcessStatus =
  | null
  | "idle"
  | "processing"
  | "completed"
  | "no_results"
  | "failed";

type BatchItem = {
  batch_id: string;
  experience_type: string;
  experience_value: number;
  created_at: string | null;
  total: number;
  pending: number;
  processing: number;
  shortlisted: number;
  rejected: number;
  failed: number;
};

const API = process.env.NEXT_PUBLIC_API_URL;
const WS = process.env.NEXT_PUBLIC_WS_URL;

const headers = {
  "ngrok-skip-browser-warning": "true",
};

function UploadSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between border rounded-2xl px-5 py-4 animate-pulse"
        >
          <div>
            <div className="h-4 w-40 bg-slate-200 rounded mb-2" />
            <div className="h-3 w-24 bg-slate-200 rounded" />
          </div>

          <div className="h-6 w-20 bg-slate-200 rounded" />
        </div>
      ))}
    </div>
  );
}

function getStatusClass(status: UploadStatus) {
  if (status === "Shortlisted") return "bg-green-100 text-green-700";
  if (status === "Rejected") return "bg-red-100 text-red-700";
  if (status === "Failed") return "bg-red-100 text-red-700";
  if (status === "Processing") return "bg-yellow-100 text-yellow-700";

  return "bg-cyan-100 text-cyan-700";
}

function formatDate(value: string | null) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString();
}

export default function DashboardPage() {
  const router = useRouter();

  const [page, setPage] = useState(1);
  const perPage = 5;

  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [loadingUploads, setLoadingUploads] = useState(false);

  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>("latest");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [uploadProcessStatus, setUploadProcessStatus] =
    useState<UploadProcessStatus>(null);

  const [stats, setStats] = useState<Stats>({
    total: 0,
    pending: 0,
    processing: 0,
    shortlisted: 0,
    rejected: 0,
    failed: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const clearMessageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const redirectedRef = useRef(false);

  const selectedBatch = useMemo(() => {
    if (selectedBatchId === "latest") return batches[0] || null;
    if (selectedBatchId === "all") return null;

    return batches.find((batch) => batch.batch_id === selectedBatchId) || null;
  }, [batches, selectedBatchId]);

  const filteredUploads = useMemo(() => {
    if (selectedBatchId === "all") {
      return uploads;
    }

    if (selectedBatchId === "latest") {
      const latestBatchId = batches[0]?.batch_id;

      if (!latestBatchId) return uploads;

      return uploads.filter((file) => file.batch_id === latestBatchId);
    }

    return uploads.filter((file) => file.batch_id === selectedBatchId);
  }, [uploads, batches, selectedBatchId]);

  const totalPages = useMemo(() => {
    return Math.max(Math.ceil(filteredUploads.length / perPage), 1);
  }, [filteredUploads.length, perPage]);

  const paginatedUploads = useMemo(() => {
    const start = (page - 1) * perPage;
    const end = start + perPage;

    return filteredUploads.slice(start, end);
  }, [filteredUploads, page, perPage]);

  const clearTimers = useCallback(() => {
    if (clearMessageTimerRef.current) {
      clearTimeout(clearMessageTimerRef.current);
      clearMessageTimerRef.current = null;
    }

    if (redirectTimerRef.current) {
      clearTimeout(redirectTimerRef.current);
      redirectTimerRef.current = null;
    }
  }, []);

  const clearUploadMessageAfterDelay = useCallback(() => {
    if (clearMessageTimerRef.current) {
      clearTimeout(clearMessageTimerRef.current);
    }

    clearMessageTimerRef.current = setTimeout(() => {
      setUploadProcessStatus(null);
      setActiveBatchId(null);
      redirectedRef.current = false;
    }, 30000);
  }, []);

  const redirectToResumeViewerAfterDelay = useCallback(
    (batchId: string) => {
      if (redirectedRef.current) return;

      redirectedRef.current = true;

      if (redirectTimerRef.current) {
        clearTimeout(redirectTimerRef.current);
      }

      redirectTimerRef.current = setTimeout(() => {
        router.push(`/resume-viewer?batch=${batchId}`);
      }, 1000);
    },
    [router]
  );

  const fetchBatches = useCallback(async () => {
    try {
      const res = await fetch(`${API}/upload/batches`, { headers });
      const data = await res.json();

      setBatches(data || []);
    } catch (err) {
      console.error("Batch fetch error:", err);
    }
  }, []);

  const fetchRecentUploads = useCallback(async () => {
    setLoadingUploads(true);

    try {
      const res = await fetch(`${API}/upload/recent?page=1&per_page=100`, {
        headers,
      });

      const result = await res.json();

      setUploads(result.data || []);
    } catch (err) {
      console.error("Recent uploads fetch error:", err);
    } finally {
      setLoadingUploads(false);
    }
  }, []);

  const refreshDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API}/upload/stats/all`, { headers });
      const data = await res.json();

      setStats({
        total: data.total || 0,
        pending: data.pending || 0,
        processing: data.processing || 0,
        shortlisted: data.shortlisted || 0,
        rejected: data.rejected || 0,
        failed: data.failed || 0,
      });
    } catch (err) {
      console.error("Stats refresh error:", err);
    }
  }, []);

  const checkExcelAndRedirect = useCallback(
    async (batchId: string) => {
      try {
        const res = await fetch(`${API}/resume/export/${batchId}`, {
          headers,
        });

        const data = await res.json();

        if (data?.excel_file) {
          setUploadProcessStatus("completed");
          clearUploadMessageAfterDelay();
          redirectToResumeViewerAfterDelay(batchId);
          return true;
        }

        return false;
      } catch (error) {
        console.error("Excel check failed:", error);
        return false;
      }
    },
    [clearUploadMessageAfterDelay, redirectToResumeViewerAfterDelay]
  );

  const checkBatchCompletion = useCallback(async () => {
    if (!activeBatchId || uploadProcessStatus !== "processing") return;

    try {
      const res = await fetch(`${API}/upload/recent?page=1&per_page=100`, {
        headers,
      });

      const result = await res.json();

      const batchFiles: UploadItem[] = (result.data || []).filter(
        (file: UploadItem) => file.batch_id === activeBatchId
      );

      if (batchFiles.length === 0) return;

      const stillProcessing = batchFiles.some(
        (file) => file.status === "Uploaded" || file.status === "Processing"
      );

      if (stillProcessing) return;

      const hasShortlisted = batchFiles.some(
        (file) => file.status === "Shortlisted"
      );

      const hasFailed = batchFiles.some((file) => file.status === "Failed");

      if (hasShortlisted) {
        await checkExcelAndRedirect(activeBatchId);
      } else if (hasFailed) {
        setUploadProcessStatus("failed");
        clearUploadMessageAfterDelay();
      } else {
        setUploadProcessStatus("no_results");
        clearUploadMessageAfterDelay();
      }

      fetchRecentUploads();
      fetchBatches();
      refreshDashboard();
    } catch (error) {
      console.error("Batch completion check failed:", error);
    }
  }, [
    activeBatchId,
    uploadProcessStatus,
    checkExcelAndRedirect,
    clearUploadMessageAfterDelay,
    fetchRecentUploads,
    fetchBatches,
    refreshDashboard,
  ]);

  useEffect(() => {
    fetchRecentUploads();
    refreshDashboard();
    fetchBatches();
  }, [fetchRecentUploads, refreshDashboard, fetchBatches]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    if (!WS || wsRef.current) return;

    const wsUrl = `${WS}/ws/dashboard`;
    const ws = new WebSocket(wsUrl);

    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected:", wsUrl);
    };

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.event === "stats_update") {
          setStats((prev) => ({
            total: data.total ?? prev.total,
            pending: data.pending ?? prev.pending,
            processing: data.processing ?? prev.processing,
            shortlisted: data.shortlisted ?? prev.shortlisted,
            rejected: data.rejected ?? prev.rejected,
            failed: data.failed ?? prev.failed,
          }));

          fetchRecentUploads();
          fetchBatches();
          return;
        }

        if (data.event === "batch_completed_no_results") {
          setUploadProcessStatus("no_results");
          fetchRecentUploads();
          fetchBatches();
          refreshDashboard();
          clearUploadMessageAfterDelay();
          return;
        }

        if (data.event === "excel_exported") {
          const batchId = data.batch_id || activeBatchId;

          if (batchId) {
            setUploadProcessStatus("completed");
            fetchRecentUploads();
            fetchBatches();
            refreshDashboard();
            clearUploadMessageAfterDelay();
            redirectToResumeViewerAfterDelay(batchId);
          }

          return;
        }

        if (data.event === "batch_completed") {
          fetchRecentUploads();
          fetchBatches();
          refreshDashboard();

          if (data.shortlisted > 0) {
            const batchId = data.batch_id || activeBatchId;

            if (batchId) {
              await checkExcelAndRedirect(batchId);
            }
          }

          return;
        }
      } catch (error) {
        console.error("WebSocket message error:", error);
      }
    };

    ws.onerror = () => {
      console.warn("WebSocket connection failed:", wsUrl);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [
    activeBatchId,
    fetchRecentUploads,
    fetchBatches,
    refreshDashboard,
    clearUploadMessageAfterDelay,
    redirectToResumeViewerAfterDelay,
    checkExcelAndRedirect,
  ]);

  useEffect(() => {
    if (!activeBatchId || uploadProcessStatus !== "processing") return;

    const interval = setInterval(() => {
      checkBatchCompletion();
    }, 3000);

    return () => clearInterval(interval);
  }, [activeBatchId, uploadProcessStatus, checkBatchCompletion]);

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return (
    <div className="space-y-8 text-slate-900">
      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-6">
        <StatCard title="Total CVs" value={stats.total} />

        <StatCard
          title="Pending"
          value={stats.pending}
          color="text-cyan-700"
        />

        <StatCard
          title="Processing"
          value={stats.processing}
          color="text-yellow-600"
        />

        <StatCard
          title="Shortlisted"
          value={stats.shortlisted}
          color="text-green-600"
        />

        <StatCard
          title="Rejected"
          value={stats.rejected}
          color="text-red-600"
        />

        <StatCard
          title="Failed"
          value={stats.failed}
          color="text-red-700"
        />
      </div>

      <UploadSection
        status={uploadProcessStatus}
        onUploadStarted={(batchId) => {
          clearTimers();
          redirectedRef.current = false;
          setActiveBatchId(batchId);
          setSelectedBatchId("latest");
          setPage(1);
          setUploadProcessStatus("processing");
          fetchRecentUploads();
          fetchBatches();
          refreshDashboard();
        }}
      />

      <div className="bg-white rounded-3xl p-6 shadow-sm overflow-visible">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
          <div>
            <h2 className="text-xl font-semibold">Recent Uploads</h2>

            {selectedBatch && (
              <p className="text-sm text-slate-500 mt-1">
                Selected batch: {selectedBatch.total} CVs,{" "}
                {selectedBatch.shortlisted} shortlisted,{" "}
                {selectedBatch.rejected} rejected
              </p>
            )}

            {selectedBatchId === "all" && (
              <p className="text-sm text-slate-500 mt-1">
                Showing all uploaded CVs
              </p>
            )}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div ref={dropdownRef} className="relative w-full sm:w-80">
              <button
                type="button"
                onClick={() => setDropdownOpen((prev) => !prev)}
                className="w-full border border-slate-300 rounded-xl px-4 py-2 text-sm text-left bg-white text-slate-700 flex justify-between items-center"
              >
                <span className="truncate">
                  {selectedBatchId === "latest"
                    ? "Latest Batch"
                    : selectedBatchId === "all"
                    ? "All Batches"
                    : selectedBatch
                    ? `${selectedBatch.total} CVs - ${
                        selectedBatch.created_at
                          ? new Date(
                              selectedBatch.created_at
                            ).toLocaleString()
                          : "-"
                      }`
                    : "Select Batch"}
                </span>

                <span className="text-slate-400 ml-2">▼</span>
              </button>

              {dropdownOpen && (
                <div className="absolute left-0 top-full mt-2 w-full bg-white border border-slate-200 rounded-xl shadow-xl z-[9999] max-h-72 overflow-y-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedBatchId("latest");
                      setPage(1);
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-cyan-50"
                  >
                    Latest Batch
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setSelectedBatchId("all");
                      setPage(1);
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-cyan-50 border-t"
                  >
                    All Batches
                  </button>

                  {batches.map((batch, index) => (
                    <button
                      key={batch.batch_id}
                      type="button"
                      onClick={() => {
                        setSelectedBatchId(batch.batch_id);
                        setPage(1);
                        setDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-cyan-50 border-t"
                    >
                      <div className="font-medium">
                        Batch {index + 1} - {batch.total} CVs
                      </div>

                      <div className="text-xs text-slate-500">
                        {batch.shortlisted} shortlisted, {batch.rejected}{" "}
                        rejected
                      </div>

                      <div className="text-xs text-slate-400">
                        {batch.created_at
                          ? new Date(batch.created_at).toLocaleString()
                          : "-"}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedBatchId !== "all" && batches.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const batchId =
                    selectedBatchId === "latest"
                      ? batches[0]?.batch_id
                      : selectedBatchId;

                  if (batchId) {
                    router.push(`/batch-details?batch=${batchId}`);
                  }
                }}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-sm whitespace-nowrap"
              >
                View Batch Details
              </button>
            )}
          </div>
        </div>

        {loadingUploads ? (
          <UploadSkeleton />
        ) : filteredUploads.length === 0 ? (
          <div className="text-center py-10 text-slate-500">
            No uploads found.
          </div>
        ) : (
          <div className="space-y-4">
            {paginatedUploads.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between border rounded-2xl px-5 py-4"
              >
                <div>
                  <a
                    href={`${API}/uploads/${file.stored_file}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-slate-900 hover:text-cyan-700"
                  >
                    {file.filename}
                  </a>

                  <p className="text-sm text-slate-500">
                    {formatDate(file.created_at)}
                  </p>
                </div>

                <span
                  className={`px-4 py-1 rounded-full text-sm ${getStatusClass(
                    file.status
                  )}`}
                >
                  {file.status}
                </span>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            <button
              disabled={page === 1}
              onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
              className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
            >
              Prev
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`px-3 py-2 rounded ${
                  p === page ? "bg-cyan-600 text-white" : "bg-slate-100"
                }`}
              >
                {p}
              </button>
            ))}

            <button
              disabled={page === totalPages}
              onClick={() =>
                setPage((prev) => Math.min(prev + 1, totalPages))
              }
              className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}