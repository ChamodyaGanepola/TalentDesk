"use client";

import StatCard from "@/app/components/StatCards";
import { ArrowLeft, Download } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

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

const headers = {
  "ngrok-skip-browser-warning": "true",
};

function getStatusClass(status: UploadStatus) {
  if (status === "Shortlisted") return "bg-green-100 text-green-700";
  if (status === "Rejected") return "bg-red-100 text-red-700";
  if (status === "Failed") return "bg-red-100 text-red-700";
  if (status === "Processing") return "bg-yellow-100 text-yellow-700";

  return "bg-cyan-100 text-cyan-700";
}

function formatDate(value: string | null) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString();
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

  return `${API}/exports/${cleanFile}`;
}

function getUploadUrl(storedFile: string) {
  const cleanFile = storedFile.replace(/\\/g, "/").replace(/^\/+/, "");

  if (cleanFile.startsWith("uploads/")) {
    return `${API}/${cleanFile}`;
  }

  return `${API}/uploads/${cleanFile}`;
}

export default function BatchDetailsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const batchId = searchParams.get("batch");

  const [batch, setBatch] = useState<Batch | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"All" | UploadStatus>("All");

  const fetchBatchDetails = useCallback(async () => {
    if (!batchId) {
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API}/upload/batch/${batchId}`, {
        headers,
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        setBatch(null);
        setUploads([]);
        return;
      }

      setBatch(data.batch);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 p-6 text-slate-900">
        <div className="bg-white rounded-3xl p-10 shadow-sm text-center text-slate-500">
          Loading batch details...
        </div>
      </div>
    );
  }

  if (!batchId || !batch) {
    return (
      <div className="min-h-screen bg-slate-100 p-6 text-slate-900">
        <div className="bg-white rounded-3xl p-10 shadow-sm text-center">
          <h2 className="text-xl font-semibold text-slate-800">
            Batch not found
          </h2>

          <p className="text-sm text-slate-500 mt-2">
            Please check whether this batch still exists in the uploads table.
          </p>

          <button
            onClick={() => router.push("/dashboard")}
            className="mt-5 px-5 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 p-6 text-slate-900">
      <div className="space-y-8">
        <div className="bg-white rounded-3xl p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <button
                onClick={() => router.push("/dashboard")}
                className="inline-flex items-center gap-2 text-sm text-cyan-700 hover:underline mb-3"
              >
                <ArrowLeft size={16} />
                Back to Dashboard
              </button>

              <h1 className="text-3xl font-bold">Batch Details</h1>

              <p className="text-sm text-slate-500 mt-1 break-all">
                Batch ID: {batch.batch_id}
              </p>

              <p className="text-sm text-slate-500">
                Uploaded: {formatDate(batch.created_at)}
              </p>
            </div>

            {batch.excel_file ? (
              <a
                href={getExcelUrl(batch.excel_file)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm"
              >
                <Download size={18} />
                Download Excel
              </a>
            ) : (
              <div className="px-5 py-3 bg-slate-100 text-slate-500 rounded-xl text-sm">
                No Excel generated
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

          <StatCard title="Failed" value={batch.failed} color="text-red-700" />
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-5">Screening Filters</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-slate-500 mb-2">Experience</p>

              <p className="font-medium">
                {formatExperienceType(batch.experience_type)}{" "}
                {batch.experience_value} years
              </p>
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
                      className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm"
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
            <h2 className="text-xl font-semibold">CVs in this Batch</h2>

            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as "All" | UploadStatus)
              }
              className="border border-slate-300 rounded-xl px-4 py-2 text-sm outline-none text-slate-700 bg-white"
            >
              <option value="All">All Status</option>
              <option value="Processing">Processing</option>
              <option value="Shortlisted">Shortlisted</option>
              <option value="Rejected">Rejected</option>
              <option value="Failed">Failed</option>
            </select>
          </div>

          {filteredUploads.length === 0 ? (
            <div className="text-center py-10 text-slate-500">
              No CVs found for this status.
            </div>
          ) : (
            <div className="space-y-4">
              {filteredUploads.map((file) => (
                <div
                  key={file.id}
                  className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border border-slate-200 rounded-2xl px-5 py-4 bg-white"
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
                      {formatDate(file.created_at)}
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
    </div>
  );
}