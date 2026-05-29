"use client";

import { useState } from "react";

type Props = {
  files: FileList;
  onClose: () => void;
  onSuccess: () => void;
};

export default function UploadFilterModal({
  files,
  onClose,
  onSuccess,
}: Props) {

  const API = process.env.NEXT_PUBLIC_API_URL;

  // =========================
  // MASTER DATA
  // =========================
  const [skills, setSkills] = useState<string[]>([
    "React",
    "Node.js",
    "Python",
    "FastAPI",
  ]);

  const [qualifications, setQualifications] = useState<string[]>([
    "BSc Computer Science",
    "MSc IT",
    "AWS Certification",
  ]);

  // =========================
  // SELECTED DATA
  // =========================
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);

  // =========================
  // EXPERIENCE FILTER
  // =========================
  const [experienceType, setExperienceType] = useState("minimum");
  const [experienceValue, setExperienceValue] = useState(4);

  // =========================
  // NEW INPUTS
  // =========================
  const [newSkill, setNewSkill] = useState("");
  const [newQualification, setNewQualification] = useState("");

  const [loading, setLoading] = useState(false);

  // =========================
  // TOGGLE SKILL
  // =========================
  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill)
        ? prev.filter((s) => s !== skill)
        : [...prev, skill]
    );
  };

  // =========================
  // TOGGLE QUALIFICATION
  // =========================
  const toggleQualification = (q: string) => {
    setSelectedQualifications((prev) =>
      prev.includes(q)
        ? prev.filter((x) => x !== q)
        : [...prev, q]
    );
  };

  // =========================
  // ADD SKILL
  // =========================
  const addSkill = () => {
    if (!newSkill.trim()) return;
    setSkills((prev) => [...prev, newSkill]);
    setNewSkill("");
  };

  // =========================
  // ADD QUALIFICATION
  // =========================
  const addQualification = () => {
    if (!newQualification.trim()) return;
    setQualifications((prev) => [...prev, newQualification]);
    setNewQualification("");
  };

  // =========================
  // UPLOAD FINAL
  // =========================
  const handleUpload = async () => {

    setLoading(true);

    const formData = new FormData();

    // files
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    // filters (IMPORTANT: backend expects JSON string)
    formData.append(
      "skills",
      JSON.stringify(selectedSkills)
    );

    formData.append(
      "qualifications",
      JSON.stringify(selectedQualifications)
    );

    formData.append("experience_type", experienceType);
    formData.append(
      "experience_value",
      String(experienceValue)
    );

    try {

      const res = await fetch(
        `${API}/upload/cvs`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();

      if (data.success) {
        onSuccess();
        onClose();
      } else {
        alert(data.message || "Upload failed");
      }

    } catch (err) {
      alert("Server error during upload");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">

      <div className="bg-white w-full max-w-3xl rounded-3xl p-6 max-h-[90vh] overflow-y-auto">

        {/* TITLE */}
        <h2 className="text-2xl font-bold mb-6">
          CV Filter Setup
        </h2>

        {/* =========================
            SKILLS
        ========================= */}
        <div className="mb-6">

          <h3 className="font-semibold mb-3">Skills</h3>

          <div className="grid grid-cols-2 gap-2">
            {skills.map((skill) => (
              <label key={skill} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedSkills.includes(skill)}
                  onChange={() => toggleSkill(skill)}
                />
                {skill}
              </label>
            ))}
          </div>

          <div className="flex gap-2 mt-3">
            <input
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              placeholder="Add skill"
              className="border px-3 py-2 rounded-xl w-full"
            />
            <button
              onClick={addSkill}
              className="bg-cyan-600 text-white px-4 rounded-xl"
            >
              Add
            </button>
          </div>

        </div>

        {/* =========================
            EXPERIENCE
        ========================= */}
        <div className="mb-6">

          <h3 className="font-semibold mb-3">
            Experience Requirement
          </h3>

          <select
            value={experienceType}
            onChange={(e) => setExperienceType(e.target.value)}
            className="border px-3 py-2 rounded-xl w-full mb-3"
          >
            <option value="minimum">Minimum</option>
            <option value="more_than">More Than</option>
            <option value="exact">Exact</option>
          </select>

          <input
            type="number"
            min={0}
            value={experienceValue}
            onChange={(e) =>
              setExperienceValue(Number(e.target.value))
            }
            className="border px-3 py-2 rounded-xl w-full"
            placeholder="Years"
          />

        </div>

        {/* =========================
            QUALIFICATIONS
        ========================= */}
        <div className="mb-6">

          <h3 className="font-semibold mb-3">
            Professional Qualifications
          </h3>

          <div className="grid grid-cols-2 gap-2">
            {qualifications.map((q) => (
              <label key={q} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedQualifications.includes(q)}
                  onChange={() => toggleQualification(q)}
                />
                {q}
              </label>
            ))}
          </div>

          <div className="flex gap-2 mt-3">
            <input
              value={newQualification}
              onChange={(e) =>
                setNewQualification(e.target.value)
              }
              placeholder="Add qualification"
              className="border px-3 py-2 rounded-xl w-full"
            />
            <button
              onClick={addQualification}
              className="bg-cyan-600 text-white px-4 rounded-xl"
            >
              Add
            </button>
          </div>

        </div>

        {/* =========================
            ACTION BUTTONS
        ========================= */}
        <div className="flex justify-end gap-3">

          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-xl"
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