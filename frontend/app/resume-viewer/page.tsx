"use client";

import { useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";

import { FileText, Eye, Download, Search, Filter } from "lucide-react";

const resumes = [
  {
    id: 1,
    name: "John Doe Resume.pdf",
    role: "Frontend Developer",
    experience: "3 Years",
    status: "Shortlisted",
    uploadedAt: "2 hours ago",
  },
  {
    id: 2,
    name: "Sarah Smith CV.pdf",
    role: "UI/UX Designer",
    experience: "5 Years",
    status: "Pending",
    uploadedAt: "5 hours ago",
  },
];

export default function ResumeViewerPage() {
  const [search, setSearch] = useState("");

  const filteredResumes = resumes.filter((resume) =>
    resume.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex min-h-screen bg-slate-100">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 p-8">
        {/* Topbar (dynamic title handled inside Topbar component) */}
        <Topbar />

        {/* Search + Filter */}
        <div className="bg-white rounded-2xl shadow-sm p-4 mb-8 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 bg-slate-100 px-4 py-3 rounded-xl w-full max-w-md">
            <Search size={18} className="text-slate-400" />

            <input
              type="text"
              placeholder="Search resumes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none w-full text-sm"
            />
          </div>

          <button className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-3 rounded-xl transition">
            <Filter size={18} />
            Filter
          </button>
        </div>

        {/* Resume List */}
        <div className="space-y-5">
          {filteredResumes.map((resume) => (
            <div
              key={resume.id}
              className="bg-white rounded-3xl shadow-sm p-6 flex items-center justify-between"
            >
              {/* Left Section */}
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 rounded-2xl bg-cyan-100 flex items-center justify-center">
                  <FileText className="text-cyan-600" size={28} />
                </div>

                <div>
                  <h2 className="font-semibold text-slate-800 text-lg">
                    {resume.name}
                  </h2>

                  <div className="flex gap-4 mt-2 text-sm text-slate-500">
                    <span>{resume.role}</span>
                    <span>Experience: {resume.experience}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 px-5 py-3 rounded-xl transition">
                  <Eye size={18} />
                  View
                </button>

                <button className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-5 py-3 rounded-xl transition">
                  <Download size={18} />
                  Download
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}