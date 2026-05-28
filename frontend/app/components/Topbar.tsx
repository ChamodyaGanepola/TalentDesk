"use client";

import { Bell, Search } from "lucide-react";
import { usePathname } from "next/navigation";

export default function Topbar() {
  const pathname = usePathname();

  const getTitle = () => {
    switch (pathname) {
      case "/dashboard":
        return "CV Screening Dashboard";
      case "/resume-viewer":
        return "Resume Viewer";
      default:
        return "Admin Panel";
    }
  };

  const getSubtitle = () => {
    switch (pathname) {
      case "/dashboard":
        return "Upload and manage candidate resumes";
      case "/resume-viewer":
        return "View and manage uploaded resumes";
      default:
        return "Manage your system";
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm p-4 flex items-center justify-between mb-8">
      {/* Left Title */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">
          {getTitle()}
        </h2>

        <p className="text-slate-500 text-sm">
          {getSubtitle()}
        </p>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-xl">
          <Search size={18} className="text-slate-400" />
          <input
            type="text"
            placeholder="Search resumes..."
            className="bg-transparent outline-none text-sm"
          />
        </div>

        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
          <Bell size={18} />
        </div>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-cyan-600 text-white flex items-center justify-center font-semibold">
            A
          </div>

          <div>
            <p className="font-semibold text-slate-700">Admin</p>
            <p className="text-xs text-slate-500">Super Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}