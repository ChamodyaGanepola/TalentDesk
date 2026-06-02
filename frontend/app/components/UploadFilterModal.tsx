"use client";

import { useState, useEffect } from "react";

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

  const [skills, setSkills] = useState<string[]>([]);
  const [qualifications, setQualifications] = useState<string[]>([]);

  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedQualifications, setSelectedQualifications] = useState<string[]>([]);

  const [experienceType, setExperienceType] = useState("minimum");
  const [experienceValue, setExperienceValue] = useState("0.7");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [newSkill, setNewSkill] = useState("");
  const [newQualification, setNewQualification] = useState("");

  // =========================
  // LOAD SKILLS / QUALIFICATIONS
  // =========================
  useEffect(() => {
    const load = async () => {
      try {
        const [s, q] = await Promise.all([
          fetch(`${API}/skills`),
          fetch(`${API}/qualifications`)
        ]);

        setSkills(await s.json());
        setQualifications(await q.json());
      } catch (err) {
        console.log(err);
      }
    };

    load();
  }, []);

  // reset when new files selected
  useEffect(() => {
    if (!files) return;

    setSelectedSkills([]);
    setSelectedQualifications([]);
    setExperienceType("minimum");
    setExperienceValue("0.7");
    setMessage("");
  }, [files]);

  // =========================
  // TOGGLES
  // =========================
  const toggleSkill = (skill: string) => {
    setSelectedSkills(prev =>
      prev.includes(skill)
        ? prev.filter(s => s !== skill)
        : [...prev, skill]
    );
  };

  const toggleQualification = (q: string) => {
    setSelectedQualifications(prev =>
      prev.includes(q)
        ? prev.filter(x => x !== q)
        : [...prev, q]
    );
  };

  // =========================
  // REFRESH
  // =========================
  const refreshSkills = async () => {
    const res = await fetch(`${API}/skills`);
    setSkills(await res.json());
  };

  const refreshQualifications = async () => {
    const res = await fetch(`${API}/qualifications`);
    setQualifications(await res.json());
  };

  // =========================
  // ADD SKILL
  // =========================
  const addSkill = async () => {
    if (!newSkill.trim()) return;

    await fetch(`${API}/skills/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newSkill })
    });

    setNewSkill("");
    refreshSkills();
  };

  // =========================
  // ADD QUALIFICATION
  // =========================
  const addQualification = async () => {
    if (!newQualification.trim()) return;

    await fetch(`${API}/qualifications/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newQualification })
    });

    setNewQualification("");
    refreshQualifications();
  };

  // =========================
  // UPLOAD
  // =========================
  const handleUpload = async () => {
    if (loading) return;

    setLoading(true);
    setMessage("");

    const formData = new FormData();

    Array.from(files).forEach(file => {
      formData.append("files", file);
    });

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

      if (data.success) {
        setMessage("✅ Upload successful! Processing started...");

        setTimeout(() => {
          onSuccess();
          onClose();
        }, 1200);
      } else {
        setMessage("❌ Upload failed: " + (data.message || "Unknown error"));
      }

    } catch (err) {
      setMessage("❌ Server error");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // CLOSE HANDLER
  // =========================
  const handleClose = () => {
    if (loading) return;

    setMessage("");
    setSelectedSkills([]);
    setSelectedQualifications([]);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">

      {/* BACKDROP */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={handleClose}
      />

      {/* MODAL */}
      <div
        className="relative bg-white text-black w-full max-w-3xl rounded-3xl p-6 max-h-[90vh] overflow-y-auto z-10"
        onClick={(e) => e.stopPropagation()}
      >

        <h2 className="text-2xl font-bold mb-4">CV Filter Setup</h2>

        {/* MESSAGE */}
        {message && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-slate-100 text-sm font-medium">
            {message}
          </div>
        )}

        {/* EXPERIENCE */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">Experience</h3>

          <select
            value={experienceType}
            onChange={(e) => setExperienceType(e.target.value)}
            className="border px-3 py-2 rounded-xl w-full mb-2"
          >
            <option value="minimum">Minimum</option>
            <option value="more_than">More Than</option>
            <option value="exact">Exact</option>
          </select>

          <input
            type="number"
            value={experienceValue}
            onChange={(e) => setExperienceValue(e.target.value)}
            className="border px-3 py-2 rounded-xl w-full"
          />
        </div>

        {/* SKILLS */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">Skills</h3>

          <div className="flex gap-2 mb-2">
            <input
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
              className="border px-3 py-2 rounded-xl w-full"
              placeholder="Add skill"
            />
            <button onClick={addSkill} className="bg-cyan-600 text-white px-4 rounded-xl">
              Add
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {skills.map(skill => (
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
        </div>

        {/* QUALIFICATIONS */}
        <div className="mb-6">
          <h3 className="font-semibold mb-2">Qualifications</h3>

          <div className="flex gap-2 mb-2">
            <input
              value={newQualification}
              onChange={(e) => setNewQualification(e.target.value)}
              className="border px-3 py-2 rounded-xl w-full"
              placeholder="Add qualification"
            />
            <button onClick={addQualification} className="bg-cyan-600 text-white px-4 rounded-xl">
              Add
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {qualifications.map(q => (
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
        </div>

        {/* ACTIONS */}
        <div className="flex justify-end gap-3">
          <button
            onClick={handleClose}
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