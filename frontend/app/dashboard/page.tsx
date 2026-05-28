"use client";

import UploadSection from "@/app/components/UploadSection";
import StatCards from "@/app/components/StatCards";
import { useEffect, useState } from "react";

export default function DashboardPage() {

  const API = process.env.NEXT_PUBLIC_API_URL;

  const [uploads, setUploads] = useState<any[]>([]);
  console.log("Uploads state:", uploads);
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    shortlisted: 0,
  });

  // =========================================
  // REFRESH DASHBOARD
  // =========================================
  const refreshDashboard = async () => {

    try {

      const [
        recentRes,
        totalRes,
        pendingRes,
        shortlistedRes
      ] = await Promise.all([
        fetch(`${API}/upload/recent`),
        fetch(`${API}/upload/stats/total`),
        fetch(`${API}/upload/stats/pending`),
        fetch(`${API}/upload/stats/shortlisted`)
      ]);

      const recent = await recentRes.json();
      const total = await totalRes.json();
      const pending = await pendingRes.json();
      const shortlisted = await shortlistedRes.json();

      setUploads(Array.isArray(recent) ? recent : []);

      setStats({
        total: total.count || 0,
        pending: pending.count || 0,
        shortlisted: shortlisted.count || 0,
      });

    } catch (err) {

      console.log("Dashboard fetch error:", err);

      setUploads([]);

      setStats({
        total: 0,
        pending: 0,
        shortlisted: 0,
      });
    }
  };

  // =========================================
  // INITIAL LOAD
  // =========================================
  useEffect(() => {
    refreshDashboard();
  }, []);

  // =========================================
  // WEBSOCKET
  // =========================================
  useEffect(() => {

    const ws = new WebSocket(
      "ws://127.0.0.1:8000/ws/dashboard"
    );

    ws.onmessage = (event) => {

      const data = JSON.parse(event.data);

      setStats((prev) => ({
        total: data.total ?? prev.total,
        pending: data.pending ?? prev.pending,
        shortlisted: data.shortlisted ?? prev.shortlisted,
      }));
    };

    ws.onerror = (err) => {
      console.log("Websocket error:", err);
    };

    return () => {
      ws.close();
    };

  }, []);

  return (
    <div className="space-y-8">

      {/* STATS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        <StatCards
          title="Total Uploaded CVs"
          value={String(stats.total)}
        />

        <StatCards
          title="Pending Review"
          value={String(stats.pending)}
          color="text-yellow-500"
        />

        <StatCards
          title="Shortlisted"
          value={String(stats.shortlisted)}
          color="text-green-600"
        />

      </div>

      {/* UPLOAD */}
      <UploadSection
        onUploadSuccess={refreshDashboard}
      />

      {/* RECENT */}
      <div className="bg-white rounded-3xl p-6 shadow-sm">

        <div className="flex items-center justify-between mb-5">

          <h2 className="text-xl font-semibold text-slate-800">
            Recent Uploads
          </h2>

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
                  {file.created_at
                    ? new Date(file.created_at).toLocaleString()
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