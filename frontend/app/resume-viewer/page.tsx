"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";

import { FileText, Eye, Download, Search, Filter } from "lucide-react";

type Resume = {
  id: number;
  name: string;
  role?: string;
  experience?: string;
  status?: string;
  uploadedAt?: string;
};

export default function ResumeViewerPage() {
  const [search, setSearch] = useState("");
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResumes = async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/upload/recent`
        );

        const data = await res.json();

        // IMPORTANT FIX: ensure array
        setResumes(Array.isArray(data) ? data : []);
      } catch (err) {
        console.log("Resume fetch error:", err);
        setResumes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchResumes();
  }, []);

  const filteredResumes = resumes.filter((r) =>
    (r.name || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />

        {/* Search */}
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

          <button className="flex items-center gap-2 bg-cyan-600 text-white px-5 py-3 rounded-xl">
            <Filter size={18} />
            Filter
          </button>
        </div>

        {/* List */}
        <div className="space-y-5">
          {loading ? (
            <p className="text-slate-500">Loading resumes...</p>
          ) : (
            filteredResumes.map((resume) => (
              <div
                key={resume.id}
                className="bg-white rounded-3xl shadow-sm p-6 flex items-center justify-between"
              >
                <div className="flex items-center gap-5">
                  <div className="w-16 h-16 rounded-2xl bg-cyan-100 flex items-center justify-center">
                    <FileText className="text-cyan-600" size={28} />
                  </div>

                  <div>
                    <h2 className="font-semibold text-slate-800 text-lg">
                      {resume.name}
                    </h2>

                    <div className="flex gap-4 mt-2 text-sm text-slate-500">
                      <span>{resume.role || "Unknown Role"}</span>
                      <span>Experience: {resume.experience || "-"}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button className="flex items-center gap-2 bg-slate-100 px-5 py-3 rounded-xl">
                    <Eye size={18} />
                    View
                  </button>

                  <button className="flex items-center gap-2 bg-cyan-600 text-white px-5 py-3 rounded-xl">
                    <Download size={18} />
                    Download
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}