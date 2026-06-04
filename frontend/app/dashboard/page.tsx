"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCards from "@/app/components/StatCards";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

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

export default function DashboardPage() {

  const router = useRouter();

  const [page, setPage] = useState(1);
  const [perPage] = useState(5);

  const [total, setTotal] = useState(0);
  const [uploads, setUploads] = useState<any[]>([]);
  const [loadingUploads, setLoadingUploads] = useState(false);

  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    shortlisted: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);

  const totalPages = Math.ceil(total / perPage);

  // =========================
  // FETCH UPLOADS
  // =========================
  const fetchRecentUploads = async (pageNumber: number) => {
    setLoadingUploads(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/upload/recent?page=${pageNumber}&per_page=${perPage}`,
        {
          headers: {
            "ngrok-skip-browser-warning": "true",
          },
        }
      );

      const result = await res.json();

      setUploads(result.data);
      setTotal(result.total);
      setPage(result.page);
    } catch (err) {
      console.log("Pagination error:", err);
    } finally {
      setLoadingUploads(false);
    }
  };

  // =========================
  // REFRESH STATS
  // =========================
  const refreshDashboard = async () => {
    try {
      const [totalRes, pendingRes, shortlistedRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload/stats/total`, {
          headers: {
            "ngrok-skip-browser-warning": "true"
          }
        }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload/stats/pending`, {
          headers: {
            "ngrok-skip-browser-warning": "true"
          }
        }),
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload/stats/shortlisted`, {
          headers: {
            "ngrok-skip-browser-warning": "true"
          }
        }),
      ]);

      const total = await totalRes.json();
      const pending = await pendingRes.json();
      const shortlisted = await shortlistedRes.json();

      setStats({
        total: total.count || 0,
        pending: pending.count || 0,
        shortlisted: shortlisted.count || 0,
      });
    } catch (err) {
      console.log(err);
    }
  };

  // =========================
  // INITIAL LOAD
  // =========================
  useEffect(() => {
    fetchRecentUploads(1);
    refreshDashboard();
  }, []);

  // =========================
  // SINGLE WEBSOCKET (FIXED)
  // =========================
  useEffect(() => {
    if (wsRef.current) return;

    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/ws/dashboard`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // ======================
      // STATS UPDATE
      // ======================
      if (data.total !== undefined) {
        setStats((prev) => ({
          total: data.total ?? prev.total,
          pending: data.pending ?? prev.pending,
          shortlisted: data.shortlisted ?? prev.shortlisted,
        }));
      }

      // ======================
      // REFRESH DATA EVENTS
      // ======================
      if (
        data.total !== undefined ||
        data.pending !== undefined ||
        data.event === "excel_exported" ||
        data.event === "batch_completed" ||
        data.event === "batch_completed_no_results"
      ) {
        fetchRecentUploads(1);
        refreshDashboard();
      }

      // ======================
      // SPECIAL EVENTS
      // ======================
      if (data.event === "excel_exported") {
        router.push("/resume-viewer");
      }

      if (data.event === "batch_completed_no_results") {
        alert("All CVs were rejected in this batch");
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [process.env.NEXT_PUBLIC_WS_URL]);

  // =========================
  // RENDER
  // =========================
  return (
    <div className="space-y-8 text-slate-900">
      {/* STATS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCards title="Total CVs" value={String(stats.total)} />
        <StatCards title="Pending" value={String(stats.pending)} />
        <StatCards title="Shortlisted" value={String(stats.shortlisted)} />
      </div>

      {/* UPLOAD */}
      <UploadSection onUploadSuccess={refreshDashboard} />

      {/* RECENT */}
      <div className="bg-white rounded-3xl p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-5">Recent Uploads</h2>

        {loadingUploads ? (
          <UploadSkeleton />
        ) : (
          <div className="space-y-4">
            {uploads.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between border rounded-2xl px-5 py-4"
              >
                <div>
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_URL}/uploads/${file.file_url.split(/[\\/]/).pop()}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {file.filename}
                  </a>

                  <p className="text-sm text-slate-500">
                    {new Date(file.created_at + "Z").toLocaleString()}
                  </p>
                </div>

                <span className="bg-cyan-100 text-cyan-700 px-4 py-1 rounded-full text-sm">
                  {file.status}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* PAGINATION */}
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            disabled={page === 1}
            onClick={() => fetchRecentUploads(page - 1)}
            className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
          >
            Prev
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => fetchRecentUploads(p)}
              className={`px-3 py-2 rounded ${p === page ? "bg-cyan-600 text-white" : "bg-slate-100"
                }`}
            >
              {p}
            </button>
          ))}

          <button
            disabled={page === totalPages}
            onClick={() => fetchRecentUploads(page + 1)}
            className="px-3 py-2 bg-slate-100 rounded disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}