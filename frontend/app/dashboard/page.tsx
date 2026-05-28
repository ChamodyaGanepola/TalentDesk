"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCards from "@/app/components/StatCards";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [uploads, setUploads] = useState<any[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    shortlisted: 0,
  });

  // 🔁 FULL REFRESH (API fallback)
  const refreshDashboard = async () => {
    const [recent, total, pending, shortlisted] = await Promise.all([
      fetch(`${API}/upload/recent`).then((r) => r.json()),
      fetch(`${API}/upload/stats/total`).then((r) => r.json()),
      fetch(`${API}/upload/stats/pending`).then((r) => r.json()),
      fetch(`${API}/upload/stats/shortlisted`).then((r) => r.json()),
    ]);

    setUploads(recent);

    setStats({
      total: total.count,
      pending: pending.count,
      shortlisted: shortlisted.count,
    });
  };

  // 🔥 INITIAL LOAD
  useEffect(() => {
    refreshDashboard();
  }, []);

  // ⚡ REAL-TIME WEBSOCKET
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/dashboard");

   ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  setStats((prev) => ({
    total: data.total ?? prev.total,
    pending: data.pending ?? prev.pending,
    shortlisted: data.shortlisted ?? prev.shortlisted,
  }));
};

    ws.onerror = (err) => {
      console.log("WebSocket error:", err);
    };

    return () => ws.close();
  }, []);

  return (
    <div className="space-y-8">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCards
          title="Total Uploaded CVs"
          value={String(stats.total || 0)}
        />

        <StatCards
          title="Pending Review"
          value={String(stats.pending || 0)}
          color="text-yellow-500"
        />

        <StatCards
          title="Shortlisted"
          value={String(stats.shortlisted || 0)}
          color="text-green-600"
        />
      </div>

      {/* Upload Section */}
      <UploadSection onUploadSuccess={refreshDashboard} />

      {/* Recent Uploads */}
      <div className="bg-white rounded-3xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-semibold text-slate-800">
            Recent Uploads
          </h2>

          <button className="text-cyan-600 hover:underline text-sm">
            View All
          </button>
        </div>

        <div className="space-y-4">
          {uploads.map((file, index) => (
            <div
              key={index}
              className="flex items-center justify-between border border-slate-200 rounded-2xl px-5 py-4"
            >
              <div>
                <h3 className="font-medium text-slate-800">
                  {file.filename}
                </h3>

                <p className="text-sm text-slate-500">
                  {file.uploaded_at
                    ? new Date(file.uploaded_at).toLocaleString()
                    : "Just now"}
                </p>
              </div>

              <span className="bg-cyan-100 text-cyan-700 px-4 py-1 rounded-full text-sm">
                {file.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}