"use client";

import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-100 flex">
      <Sidebar />

      <div className="flex-1 p-8">
        <Topbar />

        {children}
      </div>
    </div>
  );
}