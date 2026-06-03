
"use client";

import { useEffect, useState } from "react";

type Props = {
  files: FileList;
  onClose: () => void;
  onProcessingStart: (batchId: string) => void;
};

let cachedSkills: string[] | null = null;
let cachedQualifications: string[] | null = null;

export default function UploadFilterModal({
  files,
  onClose,
  onProcessingStart,
}: Props) {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [skills, setSkills] = useState<string[]>([]);
  const [qualifications, setQualifications] = useState<string[]>([]);

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);

  const [newSkill, setNewSkill] = useState("");
  const [newQualification, setNewQualification] = useState("");

  const [experienceType, setExperienceType] = useState("minimum");
  const [experienceValue, setExperienceValue] = useState("1");

  const [skillSearch, setSkillSearch] = useState("");
  const [qualSearch, setQualSearch] = useState("");

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);

  // ================= LOAD MASTER DATA =================
  useEffect(() => {
    const load = async () => {
      setLoadingData(true);

      if (cachedSkills && cachedQualifications) {
        setSkills(cachedSkills);
        setQualifications(cachedQualifications);
        setLoadingData(false);
        return;
      }

      const [s, q] = await Promise.all([
        fetch(`${API}/skills`),
        fetch(`${API}/qualifications`),
      ]);

      const sd = await s.json();
      const qd = await q.json();

      cachedSkills = sd;
      cachedQualifications = qd;

      setSkills(sd);
      setQualifications(qd);
      setLoadingData(false);
    };

    load();
  }, []);

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
  };

  const toggleQualification = (q: string) => {
    setSelectedQualifications((prev) =>
      prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q]
    );
  };

  const addSkill = async () => {
    const trimmed = newSkill.trim();
    if (!trimmed) return;

    const res = await fetch(`${API}/skills/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: trimmed }),
    });

    const data = await res.json();
    if (!data.success) return;

    setSkills((prev) => [...prev, trimmed]);
    setSelectedSkills((prev) => [...prev, trimmed]);
    setNewSkill("");
  };

  const addQualification = async () => {
    const trimmed = newQualification.trim();
    if (!trimmed) return;

    const res = await fetch(`${API}/qualifications/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: trimmed }),
    });

    const data = await res.json();
    if (!data.success) return;

    setQualifications((prev) => [...prev, trimmed]);
    setSelectedQualifications((prev) => [...prev, trimmed]);
    setNewQualification("");
  };

  // ================= UPLOAD =================
  const handleUpload = async () => {
    if (loading) return;

    setLoading(true);
    setMessage("");

    const formData = new FormData();

    Array.from(files).forEach((f) => formData.append("files", f));

    formData.append("skills", JSON.stringify(selectedSkills));
    formData.append("qualifications", JSON.stringify(selectedQualifications));
    formData.append("experience_type", experienceType);
    formData.append("experience_value", experienceValue);

    try {
      const res = await fetch(`${API}/upload/cvs`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!data.success && data.uploaded === 0) {
        setSuccess(false);
        setMessage("Upload failed");
        setLoading(false);
        return;
      }

      setSuccess(true);

      setMessage(
        data.failed_files?.length
          ? `Uploaded ${data.uploaded} files\nSome failed:\n` +
            data.failed_files.map((f: any) => `${f.file} → ${f.error}`).join("\n")
          : `Uploaded ${data.uploaded} files successfully`
      );

      // ✅ FIX: correct place to trigger processing
      if (data.batch_id) {
        onProcessingStart(data.batch_id);
      }

      if (data.uploaded === 0 && data.failed_files?.length) {
        setSuccess(false);
        setMessage("No files uploaded");
        return;
      }

      setTimeout(() => {
        onClose();
      }, 1200);

    } catch {
      setSuccess(false);
      setMessage("Server error");
    } finally {
      setLoading(false);
    }
  };


  const filteredSkills = skills.filter((s) =>
    s.toLowerCase().includes(skillSearch.toLowerCase())
  );

  const filteredQualifications = qualifications.filter((q) =>
    q.toLowerCase().includes(qualSearch.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-white w-full max-w-4xl rounded-3xl shadow-2xl z-10 overflow-hidden">
        {/* HEADER */}
        <div className="p-6 bg-cyan-600 text-white">
          <h2 className="text-xl font-bold">CV Filter Setup</h2>

          {message && (
            <div
              className={`mt-3 px-4 py-2 rounded-xl text-sm whitespace-pre-line ${success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                }`}
            >
              {message}
            </div>
          )}
        </div>

        {/* BODY */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {/* EXPERIENCE */}
          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Experience</h3>

            <div className="grid grid-cols-2 gap-3">
              <select
                value={experienceType}
                onChange={(e) => setExperienceType(e.target.value)}
                className="bg-white p-2 rounded-xl"
              >
                <option value="minimum">Minimum</option>
                <option value="more_than">More Than</option>
                <option value="exact">Exact</option>
              </select>

              <input
                type="number"
                value={experienceValue}
                onChange={(e) => setExperienceValue(e.target.value)}
                className="bg-white p-2 rounded-xl"
              />
            </div>
          </div>

          {/* SKILLS */}
          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Skills</h3>

            {/* ADD NEW SKILL */}
            <div className="flex gap-2 mb-3">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                className="bg-white rounded-xl p-2 w-full"
                placeholder="Add skill"
              />
              <button
                type="button"
                onClick={addSkill}
                className="bg-cyan-600 text-white px-4 rounded-xl"
              >
                Add
              </button>
            </div>

            <input
              value={skillSearch}
              onChange={(e) => setSkillSearch(e.target.value)}
              className="w-full p-2 bg-white rounded-xl mb-3"
              placeholder="Search skills"
            />

            <div className="grid grid-cols-2 gap-2">
              {loadingData ? (
                <p>Loading...</p>
              ) : (
                filteredSkills.map((skill) => (
                  <label key={skill} className="flex gap-2">
                    <input
                      type="checkbox"
                      checked={selectedSkills.includes(skill)}
                      onChange={() => toggleSkill(skill)}
                    />
                    {skill}
                  </label>
                ))
              )}
            </div>
          </div>

          {/* QUALIFICATIONS */}
          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Qualifications</h3>

            {/* ADD NEW QUALIFICATION */}
            <div className="flex gap-2 mb-3">
              <input
                value={newQualification}
                onChange={(e) => setNewQualification(e.target.value)}
                className="bg-white rounded-xl p-2 w-full"
                placeholder="Add qualification"
              />
              <button
                type="button"
                onClick={addQualification}
                className="bg-cyan-600 text-white px-4 rounded-xl"
              >
                Add
              </button>
            </div>

            <input
              value={qualSearch}
              onChange={(e) => setQualSearch(e.target.value)}
              className="w-full p-2 bg-white rounded-xl mb-3"
              placeholder="Search qualifications"
            />

            <div className="grid grid-cols-2 gap-2">
              {loadingData ? (
                <p>Loading...</p>
              ) : (
                filteredQualifications.map((q) => (
                  <label key={q} className="flex gap-2">
                    <input
                      type="checkbox"
                      checked={selectedQualifications.includes(q)}
                      onChange={() => toggleQualification(q)}
                    />
                    {q}
                  </label>
                ))
              )}
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <div className="p-5 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-100 rounded-xl"
          >
            Cancel
          </button>

          <button
            onClick={handleUpload}
            disabled={loading}
            className="px-5 py-2 bg-cyan-600 text-white rounded-xl"
          >
            {loading ? "Uploading..." : "Filter & Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}