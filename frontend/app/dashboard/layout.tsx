"use client";

import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";
import { prefetchMasters } from "@/app/lib/mastersCache";
import { useEffect } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    prefetchMasters();
  }, []);

  return (
    <div className="min-h-screen bg-slate-100 flex">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />
        {children}
      </main>
    </div>
  );
}