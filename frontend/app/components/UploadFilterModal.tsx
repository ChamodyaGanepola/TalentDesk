"use client";

import {
  Briefcase,
  FileText,
  GraduationCap,
  Loader2,
  Plus,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { FilterSectionSkeleton } from "@/app/components/Skeletons";
import ConfirmDialog from "@/app/components/ui/ConfirmDialog";
import { useToast } from "@/app/components/ui/Toast";
import { yearsMonthsToTotalMonths } from "@/app/lib/datetime";
import {
  addQualificationToCache,
  addSkillToCache,
  fetchMasters,
  getCachedMasters,
} from "@/app/lib/mastersCache";

type Props = {
  files: FileList;
  onClose: () => void;
  onUploadPending?: () => void;
  onUploadFailed?: () => void;
  onProcessingStart: (batchId: string, uploadedFiles: string[]) => void;
};

type FailedFile = {
  file: string;
  error: string;
};

const API = process.env.NEXT_PUBLIC_API_URL;

const headers = {
  "ngrok-skip-browser-warning": "true",
};

function ChipToggle({
  label,
  selected,
  onClick,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
        selected
          ? "bg-cyan-600 border-cyan-600 text-white shadow-sm"
          : "bg-white border-slate-200 text-slate-700 hover:border-cyan-300 hover:bg-cyan-50"
      }`}
    >
      {label}
    </button>
  );
}

function SectionCard({
  icon: Icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ElementType;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-100 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-cyan-100 text-cyan-700 flex items-center justify-center shrink-0">
          <Icon size={18} />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900">{title}</h3>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export default function UploadFilterModal({
  files,
  onClose,
  onUploadPending,
  onUploadFailed,
  onProcessingStart,
}: Props) {
  const { showToast } = useToast();
  const cached = getCachedMasters();

  const [skills, setSkills] = useState<string[]>(cached?.skills ?? []);
  const [qualifications, setQualifications] = useState<string[]>(
    cached?.qualifications ?? []
  );

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>(
    []
  );

  const [skillSearch, setSkillSearch] = useState("");
  const [qualificationSearch, setQualificationSearch] = useState("");
  const [newSkill, setNewSkill] = useState("");
  const [newQualification, setNewQualification] = useState("");

  const [experienceType, setExperienceType] = useState("minimum");
  const [experienceYears, setExperienceYears] = useState(1);
  const [experienceMonths, setExperienceMonths] = useState(0);

  const [loading, setLoading] = useState(false);
  const [skillsLoading, setSkillsLoading] = useState(!cached);
  const [qualificationsLoading, setQualificationsLoading] = useState(!cached);
  const [message, setMessage] = useState("");
  const [closeConfirmOpen, setCloseConfirmOpen] = useState(false);

  const fileArray = Array.from(files);
  const totalMonths = yearsMonthsToTotalMonths(
    experienceYears,
    experienceMonths
  );

  const experienceLabel =
    experienceType === "minimum"
      ? "Minimum"
      : experienceType === "more_than"
      ? "More than"
      : "Exactly";

  const hasFilterChanges =
    selectedSkills.length > 0 ||
    selectedQualifications.length > 0 ||
    experienceType !== "minimum" ||
    experienceYears !== 1 ||
    experienceMonths !== 0;

  const requestClose = () => {
    if (loading) return;
    if (hasFilterChanges) {
      setCloseConfirmOpen(true);
      return;
    }
    onClose();
  };

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await fetchMasters();
        if (cancelled) return;
        setSkills(data.skills);
        setQualifications(data.qualifications);
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setMessage("Failed to load skills or qualifications.");
      } finally {
        if (!cancelled) {
          setSkillsLoading(false);
          setQualificationsLoading(false);
        }
      }
    };

    if (cached) {
      setSkillsLoading(false);
      setQualificationsLoading(false);
      return;
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, [cached]);

  const filteredSkills = useMemo(() => {
    const q = skillSearch.trim().toLowerCase();
    if (!q) return skills;
    return skills.filter((s) => s.toLowerCase().includes(q));
  }, [skills, skillSearch]);

  const filteredQualifications = useMemo(() => {
    const q = qualificationSearch.trim().toLowerCase();
    if (!q) return qualifications;
    return qualifications.filter((name) => name.toLowerCase().includes(q));
  }, [qualifications, qualificationSearch]);

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  };

  const toggleQualification = (qualification: string) => {
    setSelectedQualifications((prev) =>
      prev.includes(qualification)
        ? prev.filter((q) => q !== qualification)
        : [...prev, qualification]
    );
  };

  const addSkill = async (nameOverride?: string) => {
    const name = (nameOverride ?? newSkill).trim().toLowerCase();
    if (!name) return;

    try {
      await fetch(`${API}/skills/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ name }),
      });

      addSkillToCache(name);
      setSkills((prev) => (prev.includes(name) ? prev : [...prev, name].sort()));
      setSelectedSkills((prev) => (prev.includes(name) ? prev : [...prev, name]));
      setNewSkill("");
      setSkillSearch("");
      showToast(`Skill "${name}" added.`, "success");
    } catch (err) {
      console.error(err);
      setMessage("Failed to add skill.");
      showToast("Failed to add skill.", "error");
    }
  };

  const addQualification = async (nameOverride?: string) => {
    const name = (nameOverride ?? newQualification).trim().toLowerCase();
    if (!name) return;

    try {
      await fetch(`${API}/qualifications/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ name }),
      });

      addQualificationToCache(name);
      setQualifications((prev) =>
        prev.includes(name) ? prev : [...prev, name].sort()
      );
      setSelectedQualifications((prev) =>
        prev.includes(name) ? prev : [...prev, name]
      );
      setNewQualification("");
      setQualificationSearch("");
      showToast(`Qualification "${name}" added.`, "success");
    } catch (err) {
      console.error(err);
      setMessage("Failed to add qualification.");
      showToast("Failed to add qualification.", "error");
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    setMessage("");
    onUploadPending?.();

    try {
      const formData = new FormData();

      fileArray.forEach((file) => {
        formData.append("files", file);
      });

      formData.append("skills", JSON.stringify(selectedSkills));
      formData.append("qualifications", JSON.stringify(selectedQualifications));
      formData.append("experience_type", experienceType);
      formData.append("experience_months", String(totalMonths));
      formData.append("experience_value", String(totalMonths));

      const res = await fetch(`${API}/upload/cvs`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await res.json();

      if (data.batch_id && Number(data.uploaded || 0) > 0) {
        onProcessingStart(data.batch_id, data.uploaded_files || []);
        return;
      }

      onUploadFailed?.();

      const failedMessage =
        data.failed_files
          ?.map((f: FailedFile) => `${f.file}: ${f.error}`)
          .join("\n") || data.message || "Upload failed.";

      setMessage(failedMessage);
      showToast("Upload failed. Please review the errors.", "error");
    } catch (err) {
      console.error(err);
      onUploadFailed?.();
      setMessage("Server error while uploading.");
      showToast("Server error while uploading.", "error");
    } finally {
      setLoading(false);
    }
  };

  const filePreview =
    fileArray.length <= 2
      ? fileArray.map((f) => f.name).join(", ")
      : `${fileArray[0].name}, ${fileArray[1].name} +${fileArray.length - 2} more`;

  return (
    <>
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-[2px]"
        onClick={loading ? undefined : requestClose}
        aria-hidden
      />

      <div
        className="relative bg-white w-full sm:max-w-3xl max-h-[92vh] sm:max-h-[88vh] rounded-t-3xl sm:rounded-3xl shadow-2xl z-10 flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="filter-modal-title"
      >
        <div className="shrink-0 px-5 py-4 bg-gradient-to-r from-cyan-600 to-cyan-700 text-white">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <Sparkles size={20} className="shrink-0 opacity-90" />
                <h2 id="filter-modal-title" className="text-lg font-bold">
                  Screening filters
                </h2>
              </div>
              <p
                className="text-sm text-cyan-50 mt-1 truncate"
                title={filePreview}
              >
                {fileArray.length} PDF{fileArray.length === 1 ? "" : "s"} ·{" "}
                {filePreview}
              </p>
            </div>
            <button
              type="button"
              onClick={requestClose}
              disabled={loading}
              className="shrink-0 p-2 rounded-xl bg-white/15 hover:bg-white/25 transition disabled:opacity-50"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50/80">
          {message && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm whitespace-pre-line">
              {message}
            </div>
          )}

          <SectionCard
            icon={Briefcase}
            title="Work experience"
            subtitle={`${experienceLabel} ${experienceYears}y ${experienceMonths}m (${totalMonths} months total)`}
          >
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="block">
                <span className="text-xs font-medium text-slate-500 mb-1 block">
                  Requirement
                </span>
                <select
                  value={experienceType}
                  onChange={(e) => setExperienceType(e.target.value)}
                  className="w-full bg-white p-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                >
                  <option value="minimum">Minimum</option>
                  <option value="more_than">More than</option>
                  <option value="exact">Exactly</option>
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-slate-500 mb-1 block">
                  Years
                </span>
                <select
                  value={experienceYears}
                  onChange={(e) => setExperienceYears(Number(e.target.value))}
                  className="w-full bg-white p-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                >
                  {Array.from({ length: 31 }, (_, i) => (
                    <option key={i} value={i}>
                      {i} {i === 1 ? "year" : "years"}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium text-slate-500 mb-1 block">
                  Months
                </span>
                <select
                  value={experienceMonths}
                  onChange={(e) => setExperienceMonths(Number(e.target.value))}
                  className="w-full bg-white p-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                >
                  {Array.from({ length: 12 }, (_, i) => (
                    <option key={i} value={i}>
                      {i} {i === 1 ? "month" : "months"}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </SectionCard>

          <SectionCard
            icon={Sparkles}
            title="Skills"
            subtitle={
              selectedSkills.length
                ? `${selectedSkills.length} selected`
                : "Optional — select required skills"
            }
          >
            {skillsLoading ? (
              <FilterSectionSkeleton rows={4} />
            ) : (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      value={skillSearch}
                      onChange={(e) => setSkillSearch(e.target.value)}
                      placeholder="Search or add skill..."
                      className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && skillSearch.trim()) {
                          e.preventDefault();
                          void addSkill(skillSearch);
                        }
                      }}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => void addSkill(skillSearch || newSkill)}
                    className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-sm font-medium transition"
                  >
                    <Plus size={16} />
                    Add
                  </button>
                </div>

                {selectedSkills.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedSkills.map((skill) => (
                      <ChipToggle
                        key={skill}
                        label={skill}
                        selected
                        onClick={() => toggleSkill(skill)}
                      />
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pr-1">
                  {filteredSkills.length === 0 ? (
                    <p className="text-sm text-slate-500 py-2">
                      No skills found. Type above to add one.
                    </p>
                  ) : (
                    filteredSkills
                      .filter((s) => !selectedSkills.includes(s))
                      .map((skill) => (
                        <ChipToggle
                          key={skill}
                          label={skill}
                          selected={false}
                          onClick={() => toggleSkill(skill)}
                        />
                      ))
                  )}
                </div>
              </div>
            )}
          </SectionCard>

          <SectionCard
            icon={GraduationCap}
            title="Degree & qualifications"
            subtitle={
              selectedQualifications.length
                ? `${selectedQualifications.length} selected`
                : "Optional — select required degrees"
            }
          >
            {qualificationsLoading ? (
              <FilterSectionSkeleton rows={4} />
            ) : (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />
                    <input
                      value={qualificationSearch}
                      onChange={(e) => setQualificationSearch(e.target.value)}
                      placeholder="Search or add qualification..."
                      className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-400"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && qualificationSearch.trim()) {
                          e.preventDefault();
                          void addQualification(qualificationSearch);
                        }
                      }}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      void addQualification(qualificationSearch || newQualification)
                    }
                    className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-sm font-medium transition"
                  >
                    <Plus size={16} />
                    Add
                  </button>
                </div>

                {selectedQualifications.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {selectedQualifications.map((qualification) => (
                      <ChipToggle
                        key={qualification}
                        label={qualification}
                        selected
                        onClick={() => toggleQualification(qualification)}
                      />
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto pr-1">
                  {filteredQualifications.length === 0 ? (
                    <p className="text-sm text-slate-500 py-2">
                      No qualifications found. Type above to add one.
                    </p>
                  ) : (
                    filteredQualifications
                      .filter((q) => !selectedQualifications.includes(q))
                      .map((qualification) => (
                        <ChipToggle
                          key={qualification}
                          label={qualification}
                          selected={false}
                          onClick={() => toggleQualification(qualification)}
                        />
                      ))
                  )}
                </div>
              </div>
            )}
          </SectionCard>
        </div>

        <div className="shrink-0 px-4 sm:px-5 py-4 border-t border-slate-200 bg-white">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-xs text-slate-500 flex items-center gap-1.5">
              <FileText size={14} />
              {selectedSkills.length} skills · {selectedQualifications.length}{" "}
              qualifications · {experienceLabel.toLowerCase()} {totalMonths} mo.
            </p>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={requestClose}
                disabled={loading}
                className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 transition"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleUpload}
                disabled={loading}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-sm font-medium disabled:opacity-50 transition min-w-[140px] justify-center"
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Uploading...
                  </>
                ) : (
                  "Start screening"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      open={closeConfirmOpen}
      title="Discard filters?"
      message="Your screening filter selections will be lost if you close now."
      confirmLabel="Discard"
      cancelLabel="Keep editing"
      variant="danger"
      onConfirm={() => {
        setCloseConfirmOpen(false);
        onClose();
      }}
      onCancel={() => setCloseConfirmOpen(false)}
    />
    </>
  );
}
