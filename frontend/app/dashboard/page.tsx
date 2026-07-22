"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCard from "@/app/components/StatCards";
import {
  StatCardsSkeleton,
  UploadListSkeleton,
} from "@/app/components/Skeletons";
import {
  formatSLDate,
  formatSLDateTime,
  formatSLTime,
  toSLDateKey,
} from "@/app/lib/datetime";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Filter } from "lucide-react";

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

function getStatusClass(status: UploadStatus) {
  if (status === "Shortlisted") return "bg-green-100 text-green-700";
  if (status === "Rejected") return "bg-red-100 text-red-700";
  if (status === "Failed") return "bg-red-100 text-red-700";
  if (status === "Processing") return "bg-yellow-100 text-yellow-700";

  return "bg-cyan-100 text-cyan-700";
}

function getBatchNumberOnDate(batch: BatchItem, allBatches: BatchItem[]) {
  const key = toSLDateKey(batch.created_at);
  if (!key) return 1;

  const sameDay = [...allBatches]
    .filter((item) => toSLDateKey(item.created_at) === key)
    .sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
      return aTime - bTime;
    });

  const index = sameDay.findIndex((item) => item.batch_id === batch.batch_id);
  return index >= 0 ? index + 1 : 1;
}

function formatBatchLabel(batch: BatchItem, allBatches: BatchItem[]) {
  const batchNo = getBatchNumberOnDate(batch, allBatches);
  return `${formatSLDate(batch.created_at)} | ${formatSLTime(
    batch.created_at
  )} | ${batch.total} CVs | Batch-${batchNo}`;
}

export default function DashboardPage() {
  const router = useRouter();

  const [page, setPage] = useState(1);
  const perPage = 5;

  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [loadingUploads, setLoadingUploads] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingBatches, setLoadingBatches] = useState(true);

  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>("latest");
  const [filterDate, setFilterDate] = useState<string>("");
  const [draftBatchId, setDraftBatchId] = useState<string>("latest");
  const [draftFilterDate, setDraftFilterDate] = useState<string>("");
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [uploadProcessStatus, setUploadProcessStatus] =
    useState<UploadProcessStatus>(null);
  const [completionSummary, setCompletionSummary] = useState<{
    total: number;
    shortlisted: number;
    rejected: number;
    failed: number;
  } | null>(null);

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
  const uploadsFetchIdRef = useRef(0);
  const activeBatchIdRef = useRef<string | null>(null);
  const excelWaitCountRef = useRef(0);

  useEffect(() => {
    activeBatchIdRef.current = activeBatchId;
  }, [activeBatchId]);

  const draftDateFilteredBatches = useMemo(() => {
    if (!draftFilterDate) return batches;
    return batches.filter(
      (batch) => toSLDateKey(batch.created_at) === draftFilterDate
    );
  }, [batches, draftFilterDate]);

  const draftSelectedBatch = useMemo(() => {
    const source = draftDateFilteredBatches;

    if (draftBatchId === "latest") {
      if (uploadProcessStatus === "processing" && activeBatchId) {
        return (
          source.find((batch) => batch.batch_id === activeBatchId) ||
          source[0] ||
          null
        );
      }
      return source[0] || null;
    }
    if (draftBatchId === "all") return null;

    return source.find((batch) => batch.batch_id === draftBatchId) || null;
  }, [
    draftDateFilteredBatches,
    draftBatchId,
    activeBatchId,
    uploadProcessStatus,
  ]);

  const applyFilters = useCallback(() => {
    setFilterDate(draftFilterDate);
    setSelectedBatchId(draftBatchId);
    setPage(1);
    setDropdownOpen(false);
  }, [draftFilterDate, draftBatchId]);

  const clearFilters = useCallback(() => {
    setDraftFilterDate("");
    setDraftBatchId("latest");
    setFilterDate("");
    setSelectedBatchId("latest");
    setPage(1);
    setDropdownOpen(false);
  }, []);

  const dateFilteredBatches = useMemo(() => {
    if (!filterDate) return batches;
    return batches.filter((batch) => toSLDateKey(batch.created_at) === filterDate);
  }, [batches, filterDate]);

  const selectedBatch = useMemo(() => {
    const source = dateFilteredBatches;

    if (selectedBatchId === "latest") {
      // While actively processing, keep focus on the upload batch.
      // Otherwise always default to the newest batch by date.
      if (uploadProcessStatus === "processing" && activeBatchId) {
        return (
          source.find((batch) => batch.batch_id === activeBatchId) ||
          source[0] ||
          null
        );
      }
      return source[0] || null;
    }
    if (selectedBatchId === "all") return null;

    return source.find((batch) => batch.batch_id === selectedBatchId) || null;
  }, [
    dateFilteredBatches,
    selectedBatchId,
    activeBatchId,
    uploadProcessStatus,
  ]);

  const filteredUploads = useMemo(() => {
    const batchIdsOnDate = filterDate
      ? new Set(dateFilteredBatches.map((batch) => batch.batch_id))
      : null;

    const inDate = (file: UploadItem) => {
      if (!batchIdsOnDate) {
        if (!filterDate) return true;
        return toSLDateKey(file.created_at) === filterDate;
      }
      return batchIdsOnDate.has(file.batch_id);
    };

    if (selectedBatchId === "all") {
      return uploads.filter(inDate);
    }

    if (selectedBatchId === "latest") {
      const latestBatchId =
        uploadProcessStatus === "processing" && activeBatchId
          ? activeBatchId
          : dateFilteredBatches[0]?.batch_id || batches[0]?.batch_id;

      if (!latestBatchId) return uploads.filter(inDate);

      return uploads.filter(
        (file) => file.batch_id === latestBatchId && inDate(file)
      );
    }

    return uploads.filter(
      (file) => file.batch_id === selectedBatchId && inDate(file)
    );
  }, [
    uploads,
    batches,
    dateFilteredBatches,
    selectedBatchId,
    activeBatchId,
    filterDate,
    uploadProcessStatus,
  ]);

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
      setCompletionSummary(null);
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
    } finally {
      setLoadingBatches(false);
    }
  }, []);

  const fetchRecentUploads = useCallback(async (opts?: { silent?: boolean }) => {
    const requestId = ++uploadsFetchIdRef.current;
    const silent = opts?.silent ?? false;

    if (!silent) {
      setLoadingUploads(true);
    }

    try {
      const res = await fetch(`${API}/upload/recent?page=1&per_page=100`, {
        headers,
      });

      const result = await res.json();

      // Ignore outdated responses so an older "Processing" fetch
      // cannot overwrite a newer Shortlisted/Rejected result.
      if (requestId !== uploadsFetchIdRef.current) return;

      setUploads(result.data || []);
    } catch (err) {
      if (requestId !== uploadsFetchIdRef.current) return;
      console.error("Recent uploads fetch error:", err);
    } finally {
      if (requestId === uploadsFetchIdRef.current && !silent) {
        setLoadingUploads(false);
      }
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
    } finally {
      setLoadingStats(false);
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

  const finalizeBatchFlow = useCallback(
    async (batchId: string, batchFiles: UploadItem[]) => {
      const summary = {
        total: batchFiles.length,
        shortlisted: batchFiles.filter((f) => f.status === "Shortlisted").length,
        rejected: batchFiles.filter((f) => f.status === "Rejected").length,
        failed: batchFiles.filter((f) => f.status === "Failed").length,
      };

      setCompletionSummary(summary);

      const hasShortlisted = summary.shortlisted > 0;
      const allFailed =
        batchFiles.length > 0 && summary.failed === batchFiles.length;

      // Same completion path for 1 CV or many.
      if (hasShortlisted) {
        const redirected = await checkExcelAndRedirect(batchId);

        if (redirected) {
          excelWaitCountRef.current = 0;
          return true;
        }

        // Excel may lag briefly after the last CV finishes — keep waiting.
        excelWaitCountRef.current += 1;
        if (excelWaitCountRef.current >= 10) {
          setUploadProcessStatus("completed");
          clearUploadMessageAfterDelay();
          redirectToResumeViewerAfterDelay(batchId);
          excelWaitCountRef.current = 0;
          return true;
        }

        return false;
      }

      excelWaitCountRef.current = 0;

      if (allFailed) {
        setUploadProcessStatus("failed");
        clearUploadMessageAfterDelay();
        return true;
      }

      // Rejected-only (or mixed rejected) batches: show counts and still
      // redirect to Resume Viewer so the flow always finishes.
      setUploadProcessStatus(
        summary.rejected > 0 ? "completed" : "no_results"
      );
      clearUploadMessageAfterDelay();
      redirectToResumeViewerAfterDelay(batchId);
      return true;
    },
    [
      checkExcelAndRedirect,
      clearUploadMessageAfterDelay,
      redirectToResumeViewerAfterDelay,
    ]
  );

  const checkBatchCompletion = useCallback(async () => {
    if (!activeBatchId || uploadProcessStatus !== "processing") return;

    try {
      const res = await fetch(`${API}/upload/recent?page=1&per_page=100`, {
        headers,
      });

      const result = await res.json();
      const allFiles: UploadItem[] = result.data || [];

      // Keep list in sync while CVs move Uploaded → Processing → final.
      uploadsFetchIdRef.current += 1;
      setUploads(allFiles);

      const batchFiles = allFiles.filter(
        (file) => file.batch_id === activeBatchId
      );

      if (batchFiles.length === 0) return;

      const stillProcessing = batchFiles.some(
        (file) => file.status === "Uploaded" || file.status === "Processing"
      );

      if (stillProcessing) {
        excelWaitCountRef.current = 0;
        fetchBatches();
        return;
      }

      await finalizeBatchFlow(activeBatchId, batchFiles);
      fetchBatches();
      refreshDashboard();
    } catch (error) {
      console.error("Batch completion check failed:", error);
    }
  }, [
    activeBatchId,
    uploadProcessStatus,
    finalizeBatchFlow,
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
        const currentBatchId = activeBatchIdRef.current;

        if (data.event === "stats_update") {
          setStats((prev) => ({
            total: data.total ?? prev.total,
            pending: data.pending ?? prev.pending,
            processing: data.processing ?? prev.processing,
            shortlisted: data.shortlisted ?? prev.shortlisted,
            rejected: data.rejected ?? prev.rejected,
            failed: data.failed ?? prev.failed,
          }));

          fetchRecentUploads({ silent: true });
          fetchBatches();

          // Drive the same completion flow for 1 or N CVs via polling logic.
          if (currentBatchId) {
            checkBatchCompletion();
          }
          return;
        }

        if (data.event === "batch_completed_no_results") {
          if (
            data.batch_id &&
            currentBatchId &&
            data.batch_id !== currentBatchId
          ) {
            return;
          }

          setCompletionSummary({
            total: data.total || 0,
            shortlisted: data.shortlisted || 0,
            rejected: data.rejected || 0,
            failed: data.failed || 0,
          });
          setUploadProcessStatus(
            (data.rejected || 0) > 0 ? "completed" : "no_results"
          );
          fetchRecentUploads({ silent: true });
          fetchBatches();
          refreshDashboard();
          clearUploadMessageAfterDelay();

          const batchId = data.batch_id || currentBatchId;
          if (batchId) {
            redirectToResumeViewerAfterDelay(batchId);
          }
          return;
        }

        if (data.event === "excel_exported") {
          const batchId = data.batch_id || currentBatchId;

          if (batchId) {
            if (
              typeof data.shortlisted === "number" ||
              typeof data.rejected === "number"
            ) {
              setCompletionSummary({
                total: data.total || 0,
                shortlisted: data.shortlisted || 0,
                rejected: data.rejected || 0,
                failed: data.failed || 0,
              });
            }

            setUploadProcessStatus("completed");
            fetchRecentUploads({ silent: true });
            fetchBatches();
            refreshDashboard();
            clearUploadMessageAfterDelay();
            redirectToResumeViewerAfterDelay(batchId);
          }

          return;
        }

        if (data.event === "batch_completed" || data.event === "cv_proceed") {
          setCompletionSummary({
            total: data.total || 0,
            shortlisted: data.shortlisted || 0,
            rejected: data.rejected || 0,
            failed: data.failed || 0,
          });
          fetchRecentUploads({ silent: true });
          fetchBatches();
          refreshDashboard();
          checkBatchCompletion();
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
    fetchRecentUploads,
    fetchBatches,
    refreshDashboard,
    clearUploadMessageAfterDelay,
    redirectToResumeViewerAfterDelay,
    checkBatchCompletion,
  ]);

  useEffect(() => {
    if (!activeBatchId || uploadProcessStatus !== "processing") return;

    // Run immediately so single-CV batches don't wait for the first interval.
    checkBatchCompletion();

    const interval = setInterval(() => {
      checkBatchCompletion();
    }, 2000);

    return () => clearInterval(interval);
  }, [activeBatchId, uploadProcessStatus, checkBatchCompletion]);

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return (
    <div className="space-y-8 text-slate-900">
      {loadingStats ? (
        <StatCardsSkeleton />
      ) : (
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
      )}

      <UploadSection
        status={uploadProcessStatus}
        summary={completionSummary}
        onUploadStarted={(batchId) => {
          clearTimers();
          redirectedRef.current = false;
          excelWaitCountRef.current = 0;
          setCompletionSummary(null);
          setActiveBatchId(batchId);
          setSelectedBatchId("latest");
          setDraftBatchId("latest");
          setFilterDate("");
          setDraftFilterDate("");
          setPage(1);
          setUploadProcessStatus("processing");
          fetchRecentUploads({ silent: true });
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
                Selected: {formatBatchLabel(selectedBatch, batches)} —{" "}
                {selectedBatch.shortlisted} shortlisted,{" "}
                {selectedBatch.rejected} rejected
              </p>
            )}

            {selectedBatchId === "all" && (
              <p className="text-sm text-slate-500 mt-1">
                Showing all uploaded CVs
                {filterDate ? ` on ${filterDate}` : ""}
              </p>
            )}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <input
              type="date"
              value={draftFilterDate}
              onChange={(e) => setDraftFilterDate(e.target.value)}
              className="border border-slate-300 rounded-xl px-4 py-2 text-sm bg-white text-slate-700"
              title="Filter by date"
            />

            <button
              type="button"
              onClick={applyFilters}
              className="inline-flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-xl text-sm"
            >
              <Filter size={16} />
              Filter
            </button>

            {(filterDate || selectedBatchId !== "latest") && (
              <button
                type="button"
                onClick={clearFilters}
                className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900"
              >
                Clear
              </button>
            )}

            <div ref={dropdownRef} className="relative w-full sm:w-96">
              <button
                type="button"
                onClick={() => setDropdownOpen((prev) => !prev)}
                className="w-full border border-slate-300 rounded-xl px-4 py-2 text-sm text-left bg-white text-slate-700 flex justify-between items-center"
              >
                <span className="truncate">
                  {draftBatchId === "latest"
                    ? draftSelectedBatch
                      ? `Latest — ${formatBatchLabel(draftSelectedBatch, batches)}`
                      : "Latest Batch"
                    : draftBatchId === "all"
                    ? "All Batches"
                    : draftSelectedBatch
                    ? formatBatchLabel(draftSelectedBatch, batches)
                    : "Select date & time"}
                </span>

                <span className="text-slate-400 ml-2">▼</span>
              </button>

              {dropdownOpen && (
                <div className="absolute left-0 top-full mt-2 w-full bg-white border border-slate-200 rounded-xl shadow-xl z-[9999] max-h-72 overflow-y-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setDraftBatchId("latest");
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-cyan-50"
                  >
                    Latest Batch
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setDraftBatchId("all");
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-cyan-50 border-t"
                  >
                    All Batches
                  </button>

                  {draftDateFilteredBatches.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-slate-500 border-t">
                      No batches{draftFilterDate ? ` on ${draftFilterDate}` : ""}.
                    </div>
                  ) : (
                    draftDateFilteredBatches.map((batch) => (
                      <button
                        key={batch.batch_id}
                        type="button"
                        onClick={() => {
                          setDraftBatchId(batch.batch_id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full text-left px-4 py-2 text-sm border-t ${
                          draftSelectedBatch?.batch_id === batch.batch_id
                            ? "bg-cyan-50 text-cyan-800"
                            : "hover:bg-cyan-50"
                        }`}
                      >
                        <div className="font-medium">
                          {formatBatchLabel(batch, batches)}
                          {draftDateFilteredBatches[0]?.batch_id === batch.batch_id
                            ? " · Latest"
                            : ""}
                        </div>

                        <div className="text-xs text-slate-500">
                          {batch.shortlisted} shortlisted, {batch.rejected}{" "}
                          rejected
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            {selectedBatchId !== "all" && dateFilteredBatches.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const batchId =
                    selectedBatchId === "latest"
                      ? selectedBatch?.batch_id ||
                        dateFilteredBatches[0]?.batch_id
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

        {loadingUploads || loadingBatches ? (
          <UploadListSkeleton />
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
                    {formatSLDateTime(file.created_at)}
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