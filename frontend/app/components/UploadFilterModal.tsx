"use client";

import { useEffect, useState } from "react";

type Props = {
  files: FileList;
  onClose: () => void;
  onProcessingStart: (batchId: string) => void;
};

type FailedFile = {
  file: string;
  error: string;
};

const API = process.env.NEXT_PUBLIC_API_URL;

const headers = {
  "ngrok-skip-browser-warning": "true",
};

export default function UploadFilterModal({
  files,
  onClose,
  onProcessingStart,
}: Props) {
  const [skills, setSkills] = useState<string[]>([]);
  const [qualifications, setQualifications] = useState<string[]>([]);

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);

  const [newSkill, setNewSkill] = useState("");
  const [newQualification, setNewQualification] = useState("");

  const [experienceType, setExperienceType] = useState("minimum");
  const [experienceValue, setExperienceValue] = useState("1");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const fileArray = Array.from(files);

  useEffect(() => {
    fetchMasters();
  }, []);

  const fetchMasters = async () => {
    try {
      const [skillsRes, qualificationsRes] = await Promise.all([
        fetch(`${API}/skills`, { headers }),
        fetch(`${API}/qualifications`, { headers }),
      ]);

      const skillsData = await skillsRes.json();
      const qualificationsData = await qualificationsRes.json();

      setSkills(skillsData || []);
      setQualifications(qualificationsData || []);
    } catch (err) {
      console.error(err);
      setMessage("Failed to load skills or qualifications.");
    }
  };

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill)
        ? prev.filter((s) => s !== skill)
        : [...prev, skill]
    );
  };

  const toggleQualification = (qualification: string) => {
    setSelectedQualifications((prev) =>
      prev.includes(qualification)
        ? prev.filter((q) => q !== qualification)
        : [...prev, qualification]
    );
  };

  const addSkill = async () => {
    const name = newSkill.trim().toLowerCase();

    if (!name) return;

    try {
      await fetch(`${API}/skills/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify({ name }),
      });

      setSkills((prev) => (prev.includes(name) ? prev : [...prev, name]));
      setSelectedSkills((prev) => (prev.includes(name) ? prev : [...prev, name]));
      setNewSkill("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to add skill.");
    }
  };

  const addQualification = async () => {
    const name = newQualification.trim().toLowerCase();

    if (!name) return;

    try {
      await fetch(`${API}/qualifications/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify({ name }),
      });

      setQualifications((prev) => (prev.includes(name) ? prev : [...prev, name]));
      setSelectedQualifications((prev) =>
        prev.includes(name) ? prev : [...prev, name]
      );
      setNewQualification("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to add qualification.");
    }
  };

  const handleUpload = async () => {
    setLoading(true);
    setMessage("");

    try {
      const formData = new FormData();

      fileArray.forEach((file) => {
        formData.append("files", file);
      });

      formData.append("skills", JSON.stringify(selectedSkills));
      formData.append("qualifications", JSON.stringify(selectedQualifications));
      formData.append("experience_type", experienceType);
      formData.append("experience_value", experienceValue);

      const res = await fetch(`${API}/upload/cvs`, {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        const failedMessage =
          data.failed_files
            ?.map((f: FailedFile) => `${f.file}: ${f.error}`)
            .join("\n") || data.message || "Upload failed.";

        setMessage(failedMessage);
        return;
      }

      if (data.batch_id) {
        onProcessingStart(data.batch_id);
      }

      onClose();
    } catch (err) {
      console.error(err);
      setMessage("Server error while uploading.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative bg-white w-full max-w-4xl rounded-3xl shadow-2xl z-10 overflow-hidden">
        <div className="p-6 bg-cyan-600 text-white">
          <h2 className="text-xl font-bold">CV Screening Filters</h2>

          <p className="text-sm text-cyan-50 mt-1">
            {fileArray.length} PDF file(s) selected
          </p>
        </div>

        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto text-slate-900">
          {message && (
            <div className="bg-red-100 text-red-700 p-3 rounded-xl text-sm whitespace-pre-line">
              {message}
            </div>
          )}

          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Experience</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <select
                value={experienceType}
                onChange={(e) => setExperienceType(e.target.value)}
                className="bg-white p-2 rounded-xl border border-slate-200"
              >
                <option value="minimum">Minimum</option>
                <option value="more_than">More Than</option>
                <option value="exact">Exact</option>
              </select>

              <input
                type="number"
                min="0"
                step="0.1"
                value={experienceValue}
                onChange={(e) => setExperienceValue(e.target.value)}
                className="bg-white p-2 rounded-xl border border-slate-200"
                placeholder="Experience years"
              />
            </div>
          </div>

          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Skills</h3>

            <div className="flex gap-2 mb-3">
              <input
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                placeholder="Add new skill"
                className="bg-white p-2 rounded-xl border border-slate-200 w-full"
              />

              <button
                type="button"
                onClick={addSkill}
                className="bg-cyan-600 text-white px-4 rounded-xl"
              >
                Add
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {skills.map((skill) => (
                <label key={skill} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedSkills.includes(skill)}
                    onChange={() => toggleSkill(skill)}
                  />
                  <span>{skill}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="bg-slate-50 p-4 rounded-2xl">
            <h3 className="font-semibold mb-3">Qualifications</h3>

            <div className="flex gap-2 mb-3">
              <input
                value={newQualification}
                onChange={(e) => setNewQualification(e.target.value)}
                placeholder="Add new qualification"
                className="bg-white p-2 rounded-xl border border-slate-200 w-full"
              />

              <button
                type="button"
                onClick={addQualification}
                className="bg-cyan-600 text-white px-4 rounded-xl"
              >
                Add
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {qualifications.map((qualification) => (
                <label
                  key={qualification}
                  className="flex items-center gap-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selectedQualifications.includes(qualification)}
                    onChange={() => toggleQualification(qualification)}
                  />
                  <span>{qualification}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="p-5 flex justify-end gap-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 bg-slate-100 rounded-xl disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleUpload}
            disabled={loading}
            className="px-5 py-2 bg-cyan-600 text-white rounded-xl disabled:opacity-50"
          >
            {loading ? "Uploading..." : "Filter & Upload"}
          </button>
        </div>
      </div>
    </div>
  );
}