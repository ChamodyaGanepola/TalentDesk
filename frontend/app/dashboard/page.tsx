"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCards from "@/app/components/StatCards";
import { useEffect, useState, useRef } from "react";

function StatCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm animate-pulse">
      <div className="h-3 w-24 bg-slate-200 rounded"></div>
      <div className="h-10 w-16 bg-slate-200 rounded mt-4"></div>
    </div>
  );
}

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
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [page, setPage] = useState(1);
  const [perPage] = useState(10);

  const [total, setTotal] = useState(0);
  const [uploads, setUploads] = useState<any[]>([]);
  const [loadingUploads, setLoadingUploads] = useState(false);

  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    shortlisted: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);

  // =========================
  // PAGE COUNT (IMPORTANT FIX)
  // =========================
  const totalPages = Math.ceil(total / perPage);

  // =========================
  // FETCH PAGINATED UPLOADS
  // =========================
  const fetchRecentUploads = async (pageNumber: number) => {
    setLoadingUploads(true);

    try {
      const res = await fetch(
        `${API}/upload/recent?page=${pageNumber}&per_page=${perPage}`
      );

      const result = await res.json();

      setUploads(result.data);
      setTotal(result.total);
      setPage(result.page);

      console.log("Page loaded:", result.page);
    } catch (err) {
      console.log("Pagination error:", err);
    } finally {
      setLoadingUploads(false);
    }
  };

  // =========================
  // STATS LOAD
  // =========================
  const refreshDashboard = async () => {
    try {
      const [totalRes, pendingRes, shortlistedRes] = await Promise.all([
        fetch(`${API}/upload/stats/total`),
        fetch(`${API}/upload/stats/pending`),
        fetch(`${API}/upload/stats/shortlisted`),
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
  // WEBSOCKET (UNCHANGED)
  // =========================
  useEffect(() => {
    if (wsRef.current) return;

    const ws = new WebSocket("ws://127.0.0.1:8000/ws/dashboard");
    wsRef.current = ws;

    ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.total !== undefined) {
    setStats((prev) => ({
      total: data.total ?? prev.total,
      pending: data.pending ?? prev.pending,
      shortlisted: data.shortlisted ?? prev.shortlisted,
    }));
  }

  // 
  if (data.total !== undefined || data.pending !== undefined) {
    console.log("Refreshing recent uploads due to new upload");
    fetchRecentUploads(1); // always reload latest page
  }
};

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, []);


  // RENDER
  
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
      <div className="bg-white rounded-3xl p-6 shadow-sm ">
        <h2 className="text-xl font-semibold mb-5">Recent Uploads</h2>

        {/* LIST */}
        {loadingUploads ? (
          <UploadSkeleton />
        ) : (
          <div className="space-y-4">
            {uploads.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between border rounded-2xl px-5 py-4 "
              >
               <div>
<a
  href={`${API}/uploads/${file.file_url.split(/[\\/]/).pop()}`}
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
              className={`px-3 py-2 rounded ${
                p === page ? "bg-cyan-600 text-white" : "bg-slate-100"
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