"use client";

import Sidebar from "@/app/components/Sidebar";
import Topbar from "@/app/components/Topbar";
import StatCard from "@/app/components/StatCards";
import {
  CardSkeleton,
  StatCardsSkeleton,
  UploadListSkeleton,
} from "@/app/components/Skeletons";
import {
  formatExperienceFromMonths,
  formatSLDateTime,
} from "@/app/lib/datetime";
import { professionInternLabel } from "@/app/lib/profession";
import { ArrowLeft, Download, FileSpreadsheet, Filter } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import AuthGuard from "@/app/components/AuthGuard";
import { getAuthHeaders } from "@/app/lib/auth";
import { useToast } from "@/app/components/ui/Toast";

type UploadStatus =
  | "Uploaded"
  | "Processing"
  | "Shortlisted"
  | "Rejected"
  | "Failed";

type Batch = {
  batch_id: string;
  experience_type: string;
  experience_value: number;
  experience_months?: number;
  experience_label?: string | null;
  include_internships?: boolean;
  profession?: string;
  intern_label?: string;
  created_at: string | null;
  total: number;
  pending: number;
  processing: number;
  shortlisted: number;
  rejected: number;
  failed: number;
  skills: string[];
  qualifications: string[];
  excel_file: string | null;
  excel_name?: string | null;
  excel_created_at?: string | null;
};

type UploadItem = {
  id: number;
  batch_id: string;
  filename: string;
  file_url: string;
  stored_file: string;
  status: UploadStatus;
  created_at: string | null;
};

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

function getStatusClass(status: UploadStatus) {
  if (status === "Shortlisted") return "bg-green-100 text-green-700";
  if (status === "Rejected") return "bg-red-100 text-red-700";
  if (status === "Failed") return "bg-red-100 text-red-700";
  if (status === "Processing") return "bg-yellow-100 text-yellow-700";

  return "bg-cyan-100 text-cyan-700";
}

function formatExperienceType(value: string) {
  if (value === "minimum") return "Minimum";
  if (value === "more_than") return "More Than";
  if (value === "exact") return "Exact";

  return value;
}

function getExcelUrl(excelFile: string | null) {
  if (!excelFile) return "#";

  if (excelFile.startsWith("http://") || excelFile.startsWith("https://")) {
    return excelFile;
  }

  const cleanFile = excelFile.replace(/\\/g, "/").replace(/^\/+/, "");

  if (cleanFile.startsWith("exports/")) {
    return `${API}/${cleanFile}`;
  }

  return `${API}/exports/${cleanFile.split("/").pop()}`;
}

function getUploadUrl(storedFile: string) {
  const cleanFile = storedFile.replace(/\\/g, "/").replace(/^\/+/, "");

  if (cleanFile.startsWith("uploads/")) {
    return `${API}/${cleanFile}`;
  }

  return `${API}/uploads/${cleanFile}`;
}

function BatchDetailsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();

  const batchId = searchParams.get("batch");

  const [batch, setBatch] = useState<Batch | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"All" | UploadStatus>("All");
  const [draftStatusFilter, setDraftStatusFilter] = useState<"All" | UploadStatus>("All");

  const fetchBatchDetails = useCallback(async () => {
    if (!batchId) {
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API}/upload/batch/${batchId}`, {
        headers: getAuthHeaders(),
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setBatch(null);
        setUploads([]);
        return;
      }

      const nextBatch: Batch = data.batch;

      // Fallback: if shortlisted but excel missing on batch payload, check export API.
      if (!nextBatch.excel_file && (nextBatch.shortlisted || 0) > 0) {
        try {
          const exportRes = await fetch(`${API}/resume/export/${batchId}`, {
            headers: getAuthHeaders(),
          });
          const exportData = await exportRes.json();
          if (exportData?.excel_file) {
            nextBatch.excel_file = String(exportData.excel_file).replace(
              /\\/g,
              "/"
            );
            nextBatch.excel_name = nextBatch.excel_file.split("/").pop() || null;
            if (exportData?.created_at) {
              nextBatch.excel_created_at = exportData.created_at;
            }
          }
        } catch (error) {
          console.error("Excel fallback fetch failed:", error);
        }
      }

      setBatch(nextBatch);
      setUploads(data.uploads || []);
    } catch (err) {
      console.error("Batch details fetch error:", err);
      setBatch(null);
      setUploads([]);
    } finally {
      setLoading(false);
    }
  }, [batchId]);

  useEffect(() => {
    fetchBatchDetails();
  }, [fetchBatchDetails]);

  const filteredUploads = useMemo(() => {
    if (statusFilter === "All") return uploads;

    return uploads.filter((item) => item.status === statusFilter);
  }, [uploads, statusFilter]);

  const excelLabel =
    batch?.excel_name ||
    (batch?.excel_file
      ? batch.excel_file.replace(/\\/g, "/").split("/").pop()
      : null);

  return (
    <div className="flex min-h-screen bg-slate-100">
      <Sidebar />

      <main className="flex-1 p-8">
        <Topbar />

        {loading ? (
          <div className="space-y-8">
            <CardSkeleton className="h-36" />
            <StatCardsSkeleton />
            <CardSkeleton className="h-48" />
            <UploadListSkeleton />
          </div>
        ) : !batchId || !batch ? (
          <div className="bg-white rounded-3xl p-10 shadow-sm text-center">
            <h2 className="text-xl font-semibold text-slate-800">
              Batch not found
            </h2>

            <p className="text-sm text-slate-500 mt-2">
              Please check whether this batch still exists.
            </p>

            <button
              onClick={() => router.push("/dashboard")}
              className="mt-5 px-5 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl"
            >
              Back to Dashboard
            </button>
          </div>
        ) : (
          <div className="space-y-8 text-slate-900">
            <div className="bg-white rounded-3xl p-6 shadow-sm">
              <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5">
                <div>
                  <button
                    onClick={() => router.push("/dashboard")}
                    className="inline-flex items-center gap-2 text-sm text-cyan-700 hover:underline mb-3"
                  >
                    <ArrowLeft size={16} />
                    Back to Dashboard
                  </button>

                  <h1 className="text-3xl font-bold">
                    Batch Details
                    {batch.profession?.trim()
                      ? ` — ${batch.profession.trim()}`
                      : ""}
                  </h1>

                  <p className="text-sm text-slate-500 mt-2">
                    Uploaded: {formatSLDateTime(batch.created_at)}
                  </p>

                  <p className="text-xs text-slate-400 mt-1 break-all">
                    Batch ID: {batch.batch_id}
                  </p>
                </div>

                {batch.excel_file ? (
                  <div className="rounded-2xl border border-green-100 bg-green-50 px-5 py-4 min-w-[260px]">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 rounded-xl bg-white p-2 text-green-700">
                        <FileSpreadsheet size={20} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-green-800">
                          Excel generated
                        </p>
                        <p className="text-xs text-green-700 mt-1 truncate">
                          {excelLabel}
                        </p>
                        {batch.excel_created_at ? (
                          <p className="text-xs text-green-600 mt-1">
                            Generated: {formatSLDateTime(batch.excel_created_at)}
                          </p>
                        ) : null}
                        <a
                          href={getExcelUrl(batch.excel_file)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 mt-3 text-sm font-medium text-green-800 hover:text-green-950"
                        >
                          <Download size={16} />
                          Download Excel
                        </a>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 min-w-[260px]">
                    <p className="text-sm font-semibold text-slate-700">
                      No Excel generated
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      {batch.shortlisted > 0
                        ? "Shortlisted CVs exist, but the export file is not available yet."
                        : "Excel is created only when at least one CV is shortlisted."}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-6">
              <StatCard title="Total CVs" value={batch.total} />
              <StatCard
                title="Pending"
                value={batch.pending}
                color="text-cyan-700"
              />
              <StatCard
                title="Processing"
                value={batch.processing}
                color="text-yellow-600"
              />
              <StatCard
                title="Shortlisted"
                value={batch.shortlisted}
                color="text-green-600"
              />
              <StatCard
                title="Rejected"
                value={batch.rejected}
                color="text-red-600"
              />
              <StatCard
                title="Failed"
                value={batch.failed}
                color="text-red-700"
              />
            </div>

            <div className="bg-white rounded-3xl p-6 shadow-sm">
              <h2 className="text-xl font-semibold mb-5">Screening Filters</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
                <div>
                  <p className="text-sm text-slate-500 mb-2">Position</p>
                  <p className="font-medium">
                    {batch.profession?.trim()
                      ? batch.profession
                      : "Not specified"}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-slate-500 mb-2">Experience</p>
                  <p className="font-medium">
                    {formatExperienceType(batch.experience_type)}{" "}
                    {batch.experience_label ||
                      formatExperienceFromMonths(
                        batch.experience_months ?? batch.experience_value
                      )}
                  </p>
                </div>

                <div className="min-w-0">
                  <p className="text-sm text-slate-500 mb-2">Internships</p>
                  <p className="font-medium">
                    {batch.include_internships === false
                      ? "Excluded from experience"
                      : "Included in experience"}
                  </p>
                  {(batch.intern_label?.trim() ||
                    batch.profession?.trim()) && (
                    <p
                      className="text-xs text-slate-500 mt-1 truncate"
                      title={
                        batch.intern_label?.trim() ||
                        professionInternLabel(batch.profession || "")
                      }
                    >
                      {batch.intern_label?.trim() ||
                        professionInternLabel(batch.profession || "")}
                    </p>
                  )}
                </div>

                <div>
                  <p className="text-sm text-slate-500 mb-2">Skills</p>
                  {batch.skills.length === 0 ? (
                    <p className="text-slate-400">No skills selected</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {batch.skills.map((skill) => (
                        <span
                          key={skill}
                          className="px-3 py-1 bg-cyan-50 text-cyan-700 rounded-full text-sm"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-sm text-slate-500 mb-2">Qualifications</p>
                  {batch.qualifications.length === 0 ? (
                    <p className="text-slate-400">No qualifications selected</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {batch.qualifications.map((qualification) => (
                        <span
                          key={qualification}
                          className="px-3 py-1 bg-slate-100 text-slate-700 rounded-full text-sm"
                        >
                          {qualification}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-3xl p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-5">
                <div>
                  <h2 className="text-xl font-semibold">CVs in this Batch</h2>
                  <p className="text-sm text-slate-500 mt-1">
                    Showing {filteredUploads.length} of {uploads.length} CVs
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <select
                    value={draftStatusFilter}
                    onChange={(e) =>
                      setDraftStatusFilter(e.target.value as "All" | UploadStatus)
                    }
                    className="border border-slate-300 rounded-xl px-4 py-2 text-sm outline-none text-slate-700 bg-white"
                  >
                    <option value="All">All Status</option>
                    <option value="Uploaded">Uploaded</option>
                    <option value="Processing">Processing</option>
                    <option value="Shortlisted">Shortlisted</option>
                    <option value="Rejected">Rejected</option>
                    <option value="Failed">Failed</option>
                  </select>

                  <button
                    type="button"
                    onClick={() => {
                      setStatusFilter(draftStatusFilter);
                      showToast("Status filter applied.", "success");
                    }}
                    className="inline-flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-xl text-sm"
                  >
                    <Filter size={16} />
                    Filter
                  </button>

                  {statusFilter !== "All" && (
                    <button
                      type="button"
                      onClick={() => {
                        setDraftStatusFilter("All");
                        setStatusFilter("All");
                        showToast("Status filter cleared.", "info");
                      }}
                      className="px-3 py-2 text-sm text-slate-600 hover:text-slate-900"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {filteredUploads.length === 0 ? (
                <div className="text-center py-10 text-slate-500">
                  No CVs found for this status.
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredUploads.map((file) => (
                    <div
                      key={file.id}
                      className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-slate-200 rounded-2xl px-5 py-4 hover:border-cyan-200 transition"
                    >
                      <div>
                        <a
                          href={getUploadUrl(file.stored_file)}
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
                        className={`px-4 py-1 rounded-full text-sm w-fit ${getStatusClass(
                          file.status
                        )}`}
                      >
                        {file.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function BatchDetailsPage() {
  return (
    <AuthGuard>
      <Suspense
        fallback={
          <div className="min-h-screen bg-slate-100 p-8 text-slate-500">
            Loading batch details...
          </div>
        }
      >
        <BatchDetailsContent />
      </Suspense>
    </AuthGuard>
  );
}
